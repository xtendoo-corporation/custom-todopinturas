# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.exceptions import UserError


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    xtd_effect_on_validate = fields.Boolean(
        string="Contabilizar efecto al validar la factura",
        help=(
            "Al validar una factura con este modo de pago, se crea y "
            "contabiliza automáticamente un pago que reclasifica el importe "
            "de la cuenta de clientes (430) a la cuenta puente del método de "
            "pago (p.ej. 411000); la factura queda 'en proceso de pago', no "
            "'pagada'. Pieza independiente de la gestión de descuento al "
            "subir la orden de cobro (más abajo), que por ahora sigue "
            "esperando encontrar el 430 sin conciliar."
        ),
    )
    xtd_manage_effects_discount = fields.Boolean(
        string="Gestionar descuento de efectos",
        help=(
            "Si está marcado, al subir el fichero de la orden de cobro, los "
            "efectos que TODAVÍA NO hayan vencido se reclasifican a la cuenta "
            "de efectos pendientes de vencer y se contabiliza el anticipo del "
            "banco (descuento) en una cuenta de deuda; se liquidan solos en su "
            "fecha de vencimiento. Los efectos ya vencidos en el momento de "
            "subir el fichero no se tocan: siguen el circuito nativo (cuenta "
            "puente del método de pago -> banco, vía conciliación normal)."
        ),
    )
    xtd_pending_effects_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta de efectos pendientes de vencer",
        check_company=True,
        help=(
            "Cuenta (p.ej. 411001) a la que se reclasifican los efectos "
            "todavía no vencidos cuando se suben al banco, en sustitución de "
            "la cuenta puente general del método de pago."
        ),
    )
    xtd_discounted_effects_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta de deudas por efectos descontados",
        check_company=True,
        help=(
            "Cuenta (habitualmente del grupo 520) que recoge la deuda con el "
            "banco mientras el efecto está pendiente de vencer."
        ),
    )

    def _xtd_effects_accounts_or_raise(self):
        self.ensure_one()
        if not self.xtd_pending_effects_account_id or not self.xtd_discounted_effects_account_id:
            raise UserError(
                self.env._(
                    "Configura la cuenta de efectos pendientes de vencer y la"
                    " cuenta de efectos descontados en el modo de pago '%s'"
                    " antes de subir la remesa.",
                    self.display_name,
                )
            )
        return self.xtd_pending_effects_account_id, self.xtd_discounted_effects_account_id
