from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

# Campos que no se pueden modificar a mano en el pedido de venta
LOCKED_FIELDS = ("validity_date", "pricelist_id")
# Si se escribe alguno de estos a la vez, el cambio viene del recálculo
# automático del pedido (nuevo cliente, compañía o fecha), no de una edición manual.
RECOMPUTE_DRIVERS = ("partner_id", "company_id", "date_order")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.constrains("partner_id")
    def _check_partner_pos_credit_sale_enabled(self):
        for order in self:
            partner = order.partner_id
            if not partner:
                continue
            if not (
                partner.pos_credit_sale_enabled
                or partner.commercial_partner_id.pos_credit_sale_enabled
            ):
                raise ValidationError(
                    _(
                        "No se puede vender a «%s» porque no tiene permitida la "
                        "venta a crédito en POS.",
                        partner.display_name,
                    )
                )

    def write(self, vals):
        if (
            not self.env.su
            and any(f in vals for f in LOCKED_FIELDS)
            and not any(f in vals for f in RECOMPUTE_DRIVERS)
        ):
            for order in self:
                for fname in LOCKED_FIELDS:
                    if fname in vals and order._locked_value_changed(
                        fname, vals[fname]
                    ):
                        raise UserError(
                            _(
                                "No se puede modificar el campo «%s» del pedido de venta.",
                                order._fields[fname].get_description(self.env)[
                                    "string"
                                ],
                            )
                        )
        return super().write(vals)

    def _locked_value_changed(self, fname, value):
        self.ensure_one()
        field = self._fields[fname]
        new = field.convert_to_cache(value, self, validate=False)
        current = field.convert_to_cache(self[fname], self, validate=False)
        return new != current
