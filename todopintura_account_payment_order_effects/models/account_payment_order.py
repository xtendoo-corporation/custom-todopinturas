# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    # draft2open() is intentionally left untouched for every mode,
    # including xtd_effect_chain_enabled ones: "Confirmar pagos" only
    # changes state (draft -> open), it never books an entry. Stage 1
    # (430 -> cuenta de efectos en cartera) already happened earlier, at
    # invoice validation, via xtd_effect_on_validate -- the account.payment
    # this order creates from the picked-up line is a harmless, unposted
    # placeholder; the real accounting for stages 2/3 acts on the ORIGINAL
    # validation-time payment instead (see _xtd_chain_original_payments()).

    def _xtd_chain_original_payments(self):
        """The account.payment created at invoice validation
        (xtd_effect_on_validate) for each line in this order -- the one
        whose still-open line in the "efectos en cartera" account stages 2
        and 3 act on. NOT ``self.payment_ids`` (the order's own, native,
        never-posted-for-this-flow payment)."""
        self.ensure_one()
        original_payments = self.payment_line_ids.move_line_id.payment_id
        if not original_payments:
            raise UserError(
                self.env._(
                    "Ninguna de las facturas de la orden %s tiene un pago de"
                    " efecto (¿validaste la factura con 'Contabilizar efecto"
                    " al validar la factura' activado?).",
                    self.name,
                )
            )
        return original_payments

    def open2generated(self):
        res = super().open2generated()
        for order in self:
            if order.payment_mode_id.xtd_effect_chain_enabled:
                order.payment_mode_id._xtd_chain_accounts_or_raise()
                order._xtd_chain_original_payments().xtd_create_chain_remesado_move(order)
        return res

    def generated2uploaded(self):
        chain_orders = self.filtered(
            lambda o: o.payment_mode_id.xtd_effect_chain_enabled
        )
        normal_orders = self - chain_orders

        for order in normal_orders:
            if order.payment_mode_id.xtd_manage_effects_discount:
                # Fail fast, before anything gets posted/reconciled, if the
                # payment mode is not fully configured for effect discount.
                order.payment_mode_id._xtd_effects_accounts_or_raise()

        res = True
        if normal_orders:
            res = super(AccountPaymentOrder, normal_orders).generated2uploaded()
        for order in normal_orders:
            if order.payment_mode_id.xtd_manage_effects_discount:
                order.payment_ids.xtd_create_discount_move()

        for order in chain_orders:
            # Native post_and_reconcile() is deliberately NEVER called for
            # these orders: the real payment (and its 430 -> puente entry)
            # already exists from validation time: there is nothing left to
            # post here, only the remaining stage of OUR OWN chain to close.
            order._xtd_chain_original_payments().xtd_close_chain_remesado_move(order)
            order.write(
                {
                    "state": "uploaded",
                    "date_uploaded": fields.Date.context_today(order),
                }
            )
        return res
