# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Perfiles bloqueados: no modifican precios, descuentos, condiciones ni modos de pago.

Un usuario esta *bloqueado* si tiene alguno de los perfiles Todopintura (grupo tecnico
``group_todopintura_restricted``) y NO tiene el grupo
``group_todopintura_commercial_editor`` (que implican Direccion y los administradores).
Los procesos del sistema (``sudo``) no se ven afectados.
"""
from odoo import api, fields, models

MODULE = "todopintura_user_groups"

# Campos de las lineas de venta que un usuario bloqueado no puede fijar: se recalculan
# siempre desde la tarifa y las condiciones del cliente.
LINE_LOCKED_FIELDS = ("price_unit", "discount")
# Condiciones y modos de pago (cabecera de pedidos y facturas).
ORDER_LOCKED_FIELDS = ("payment_term_id", "payment_mode_id")
INVOICE_LOCKED_FIELDS = ("invoice_payment_term_id", "payment_mode_id")


class ResUsers(models.Model):
    _inherit = "res.users"

    def _todopintura_is_locked(self):
        self.ensure_one()
        return self.has_group(f"{MODULE}.group_todopintura_restricted") and not self.has_group(
            f"{MODULE}.group_todopintura_commercial_editor"
        )


class TodopinturaLockMixin(models.AbstractModel):
    _name = "todopintura.lock.mixin"
    _description = "Bloqueo de precios, descuentos y condiciones de pago"

    todopintura_locked = fields.Boolean(compute="_compute_todopintura_locked")

    _todopintura_locked_fields = ()
    # Al crear se respeta lo que envie el codigo (facturas desde pedidos, anticipos...):
    # la interfaz ya los muestra en solo lectura, asi que no los envia.
    _todopintura_strip_on_create = False

    def _compute_todopintura_locked(self):
        locked = not self.env.su and self.env.user._todopintura_is_locked()
        for record in self:
            record.todopintura_locked = locked

    @api.model
    def _todopintura_strip(self, vals):
        """Quita de ``vals`` los campos bloqueados; el ORM los recalcula solo."""
        if self.env.su or not self.env.user._todopintura_is_locked():
            return vals
        return {k: v for k, v in vals.items() if k not in self._todopintura_locked_fields}

    @api.model_create_multi
    def create(self, vals_list):
        if self._todopintura_strip_on_create:
            vals_list = [self._todopintura_strip(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        return super().write(self._todopintura_strip(vals))


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "todopintura.lock.mixin"]

    _todopintura_locked_fields = ORDER_LOCKED_FIELDS
    _todopintura_strip_on_create = True


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "todopintura.lock.mixin"]

    _todopintura_locked_fields = LINE_LOCKED_FIELDS


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "todopintura.lock.mixin"]

    _todopintura_locked_fields = INVOICE_LOCKED_FIELDS


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "todopintura.lock.mixin"]

    _todopintura_locked_fields = LINE_LOCKED_FIELDS


class PosResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _load_pos_data_read(self, records, config):
        """El TPV trata a los perfiles bloqueados como rol ``minimal``: sin descuento
        manual, sin cambio de precio y sin cambio de signo en las lineas."""
        read_records = super()._load_pos_data_read(records, config)
        if read_records and records.filtered(lambda u: u._todopintura_is_locked()):
            read_records[0]["_role"] = "minimal"
        return read_records
