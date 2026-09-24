# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generated2uploaded(self):
        for order in self:
            if order.payment_mode_id.xtd_manage_effects_discount:
                # Fail fast, before anything gets posted/reconciled, if the
                # payment mode is not fully configured for effect discount.
                order.payment_mode_id._xtd_effects_accounts_or_raise()
        res = super().generated2uploaded()
        for order in self:
            if order.payment_mode_id.xtd_manage_effects_discount:
                order.payment_ids.xtd_create_discount_move()
        return res
