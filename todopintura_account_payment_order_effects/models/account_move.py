# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    xtd_effect_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Pago del efecto",
        readonly=True,
        copy=False,
        help="Pago creado automáticamente al validar la factura, cuando su "
        "modo de pago gestiona efectos: reclasifica el importe de la cuenta "
        "de clientes a la cuenta puente del método de pago (p.ej. 411000).",
    )

    def action_open_xtd_effect_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "form",
            "res_id": self.xtd_effect_payment_id.id,
            "target": "current",
        }

    def _get_invoice_in_payment_state(self):
        """Show "in_payment" for invoices covered by our own effect payment,
        without needing account_payment_order's own payment-line/order
        machinery (that one is reserved for the real Orden de cobro
        submission later) or the Enterprise accounting app."""
        if self.xtd_effect_payment_id:
            return "in_payment"
        return super()._get_invoice_in_payment_state()

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        posted.filtered(
            lambda move: move.move_type == "out_invoice"
            and move.payment_mode_id.xtd_effect_on_validate
            and not move.xtd_effect_payment_id
        )._xtd_create_effect_payment()
        return posted

    def _xtd_create_effect_payment(self):
        for invoice in self:
            mode = invoice.payment_mode_id
            if mode.bank_account_link != "fixed":
                raise UserError(
                    self.env._(
                        "La gestión automática de efectos al validar la"
                        " factura solo está soportada para modos de pago con"
                        " banco fijo. Revisa el modo de pago '%s'.",
                        mode.display_name,
                    )
                )
            journal = mode.fixed_journal_id
            if not journal:
                raise UserError(
                    self.env._(
                        "El modo de pago '%s' no tiene diario de banco fijo"
                        " configurado.",
                        mode.display_name,
                    )
                )
            method_line = self.env["account.payment.method.line"].search(
                [
                    ("payment_method_id", "=", mode.payment_method_id.id),
                    ("journal_id", "=", journal.id),
                ],
                limit=1,
            )
            if not method_line:
                raise UserError(
                    self.env._(
                        "No se encontró una línea de método de pago '%s' en"
                        " el diario '%s'.",
                        mode.payment_method_id.display_name,
                        journal.display_name,
                    )
                )
            receivable_line = invoice.line_ids.filtered(
                lambda line: line.account_id.account_type == "asset_receivable"
                and not line.reconciled
            )
            if not receivable_line:
                continue

            payment = self.env["account.payment"].create(
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": invoice.partner_id.id,
                    "amount": invoice.amount_residual,
                    "currency_id": invoice.currency_id.id,
                    "journal_id": journal.id,
                    "payment_method_line_id": method_line.id,
                    "destination_account_id": receivable_line.account_id.id,
                    "date": invoice.invoice_date or fields.Date.context_today(self),
                    "memo": invoice.name,
                }
            )
            payment.action_post()
            # Set this BEFORE reconciling: reconcile() triggers a recompute
            # of invoice.payment_state right away, and our own
            # _get_invoice_in_payment_state() override depends on this field
            # being already set to return "in_payment" instead of "paid".
            invoice.xtd_effect_payment_id = payment.id
            # The outstanding line inherits the payment's own date (today) as
            # its maturity date by default; force it to the invoice's real
            # due date instead, since that's what later drives the "vencido
            # / no vencido" branching once this line is picked up by an
            # Orden de cobro (see wizard/account_payment_line_create.py and
            # account_payment.py's due-date checks).
            outstanding_line = payment._seek_for_lines()[0]
            outstanding_line.date_maturity = (
                invoice.invoice_date_due or invoice.invoice_date
            )
            counterpart_line = payment._seek_for_lines()[1]
            (receivable_line + counterpart_line).reconcile()
