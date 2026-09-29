# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models
from odoo.fields import Domain


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = "account.payment.line.create"

    @api.depends(
        "date_type",
        "due_on",
        "filter_date",
        "filter_date_end",
        "journal_ids",
        "invoice",
        "target_move",
        "payment_mode",
        "partner_ids",
    )
    def _compute_move_line_domain(self):
        super()._compute_move_line_domain()
        self.ensure_one()
        effects_domain = self._xtd_effects_move_line_domain()
        if effects_domain:
            self.move_line_domain = Domain.OR([self.move_line_domain, effects_domain])

    def _xtd_effects_move_line_domain(self):
        """Lines eligible because an invoice on this payment mode was
        already covered by SOME inbound payment (our own effect payment at
        validation time, or a plain manual "Registrar pago"), whose
        outstanding line still sits open in a non-receivable bridge account
        (e.g. 411000 for Giro, 572003 "Pagos pendientes" for Pagaré).

        This is deliberately generic: it does not assume a specific
        payment_method_line or journal, since a "variable" bank_account_link
        mode (like Pagaré here) can have several. It only requires that the
        invoice's own payment_mode_id matches the order's, and that the
        payment's bridge account allows reconciliation.
        """
        self.ensure_one()
        order = self.order_id
        if order.payment_type != "inbound":
            return None
        mode = order.payment_mode_id
        if not mode:
            return None

        candidates = self.env["account.move.line"].search(
            [
                ("reconciled", "=", False),
                ("company_id", "=", order.company_id.id),
                ("debit", ">", 0),
                ("account_id.account_type", "not in", ("asset_receivable", "liability_payable")),
                ("account_id.reconcile", "=", True),
                ("payment_id", "!=", False),
                ("payment_id.payment_type", "=", "inbound"),
            ]
        )
        matching = candidates.filtered(
            lambda line, mode=mode: mode in line.payment_id.reconciled_invoice_ids.payment_mode_id
        )
        if not matching:
            return None

        domain = [("id", "in", matching.ids)]
        if self.partner_ids:
            domain += [("partner_id", "in", self.partner_ids.ids)]
        if self.target_move == "posted":
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ("draft", "posted"))]
        if self.date_type == "due":
            if self.due_on == "between":
                domain += [
                    "&",
                    ("date_maturity", ">=", self.filter_date),
                    ("date_maturity", "<=", self.filter_date_end),
                ]
            else:
                domain += [
                    "|",
                    ("date_maturity", self.due_on, self.filter_date),
                    ("date_maturity", "=", False),
                ]
        elif self.date_type == "move":
            if self.due_on == "between":
                domain += [
                    "&",
                    ("date", ">=", self.filter_date),
                    ("date", "<=", self.filter_date_end),
                ]
            else:
                domain.append(("date", self.due_on, self.filter_date))

        paylines = self.env["account.payment.line"].search(
            [
                ("state", "in", ("draft", "open", "generated")),
                ("move_line_id", "!=", False),
            ]
        )
        if paylines:
            domain += [("id", "not in", paylines.move_line_id.ids)]
        return domain
