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
        """Lines eligible via "contabilizar efecto al validar la factura"
        (see account_move.py): the outstanding line of the account.payment
        created at invoice validation, still unreconciled -- i.e. still
        pending to actually be sent to the bank. These live in the payment
        method's bridge account (e.g. 411000), not in a receivable/payable
        account, so the native wizard domain never finds them.
        """
        self.ensure_one()
        order = self.order_id
        if order.payment_type != "inbound":
            return None
        mode = order.payment_mode_id
        if not mode.xtd_effect_on_validate:
            return None
        method_line = self._xtd_effect_method_line(mode)
        if not method_line or not method_line.payment_account_id:
            return None

        domain = [
            ("reconciled", "=", False),
            ("company_id", "=", order.company_id.id),
            ("account_id", "=", method_line.payment_account_id.id),
            ("payment_id.payment_method_line_id", "=", method_line.id),
        ]
        # Deliberately NOT filtered by self.journal_ids: that filter targets
        # the journal of the ORIGINAL invoice (e.g. Ventas), but this line
        # belongs to the effect payment's own move, whose journal is the
        # bank journal itself -- an unrelated concept here, since the
        # payment_method_line_id condition above already fully pins down
        # which flow these lines belong to.
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

    def _xtd_effect_method_line(self, mode):
        if mode.bank_account_link != "fixed" or not mode.fixed_journal_id:
            return self.env["account.payment.method.line"]
        return self.env["account.payment.method.line"].search(
            [
                ("payment_method_id", "=", mode.payment_method_id.id),
                ("journal_id", "=", mode.fixed_journal_id.id),
            ],
            limit=1,
        )
