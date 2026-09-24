# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import Command, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    xtd_effect_state = fields.Selection(
        selection=[
            ("collected", "Cobrado directamente"),
            ("discounted", "Anticipado por el banco"),
            ("settled", "Liquidado"),
        ],
        string="Estado del efecto",
        copy=False,
        tracking=True,
    )
    xtd_collection_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Asiento de cobro directo",
        readonly=True,
        copy=False,
        help="Efectos ya vencidos en el momento de subir la remesa: se "
        "cancela directamente la cuenta puente contra el banco, sin pasar "
        "por el circuito de descuento.",
    )
    xtd_discount_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Asiento de anticipo",
        readonly=True,
        copy=False,
    )
    xtd_settlement_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Asiento de liquidación",
        readonly=True,
        copy=False,
    )
    xtd_pending_effect_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Apunte de efecto pendiente de vencer",
        readonly=True,
        copy=False,
        help="Línea en la cuenta de efectos pendientes de vencer abierta al "
        "descontar el efecto; se reconcilia al liquidarlo en su vencimiento.",
    )

    def xtd_create_discount_move(self):
        """Process effects right after uploading the payment order's file.

        Called from ``account.payment.order.generated2uploaded()``. Splits
        in two branches depending on the effect's maturity date:
        - Already due (or due today): the money is really being collected
          now, so the bridge account is closed directly against the bank
          (411000 -> 572), immediately, no waiting for a real bank statement.
        - Not yet due: nothing has really been collected, so instead the
          bridge account is reclassified to the "efectos pendientes de
          vencer" account (no cash impact) and the bank's cash advance is
          recognized against a "efectos descontados" debt account, to be
          cancelled at maturity by the settlement cron.
        """
        today = fields.Date.context_today(self)
        for payment in self:
            mode = payment.payment_order_id.payment_mode_id
            if not mode.xtd_manage_effects_discount:
                continue
            if payment.xtd_effect_state or not payment.move_id:
                continue
            bank_account = payment.journal_id.default_account_id
            if not bank_account:
                raise UserError(
                    self.env._(
                        "El diario '%s' no tiene configurada una cuenta"
                        " contable.",
                        payment.journal_id.display_name,
                    )
                )
            due_date = payment.payment_line_date
            if not due_date or due_date <= today:
                payment._xtd_create_collection_move(bank_account)
            else:
                payment._xtd_create_discount_move_one(mode, bank_account)
        return True

    def _xtd_create_collection_move(self, bank_account):
        """Already-due effect: close the bridge account straight to the bank."""
        self.ensure_one()
        general_line = self._seek_for_lines()[0]
        label = self.env._("Cobro efecto %s", self.name)
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_id.id,
                "date": fields.Date.context_today(self),
                "ref": label,
                "line_ids": [
                    Command.create(
                        {
                            "name": label,
                            "account_id": bank_account.id,
                            "partner_id": self.partner_id.id,
                            "debit": self.amount,
                            "credit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": label,
                            "account_id": general_line.account_id.id,
                            "partner_id": self.partner_id.id,
                            "debit": 0.0,
                            "credit": self.amount,
                        }
                    ),
                ],
            }
        )
        move._post()
        new_general_line = move.line_ids.filtered(
            lambda line, acc=general_line.account_id: line.account_id == acc
        )
        (general_line + new_general_line).reconcile()
        self.write({"xtd_collection_move_id": move.id, "xtd_effect_state": "collected"})

    def _xtd_create_discount_move_one(self, mode, bank_account):
        """Not-yet-due effect: reclassify to 'pendientes de vencer' and
        recognize the bank's cash advance against the 'efectos descontados'
        debt account."""
        self.ensure_one()
        pending_account, discounted_account = mode._xtd_effects_accounts_or_raise()
        general_line = self._seek_for_lines()[0]
        label = self.env._("Anticipo banco efecto %s", self.name)
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_id.id,
                "date": fields.Date.context_today(self),
                "ref": label,
                "line_ids": [
                    Command.create(
                        {
                            "name": label,
                            "account_id": bank_account.id,
                            "partner_id": self.partner_id.id,
                            "debit": self.amount,
                            "credit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": label,
                            "account_id": discounted_account.id,
                            "partner_id": self.partner_id.id,
                            "debit": 0.0,
                            "credit": self.amount,
                        }
                    ),
                    Command.create(
                        {
                            "name": label,
                            "account_id": pending_account.id,
                            "partner_id": self.partner_id.id,
                            "debit": self.amount,
                            "credit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": label,
                            "account_id": general_line.account_id.id,
                            "partner_id": self.partner_id.id,
                            "debit": 0.0,
                            "credit": self.amount,
                        }
                    ),
                ],
            }
        )
        move._post()
        new_general_line = move.line_ids.filtered(
            lambda line, acc=general_line.account_id: line.account_id == acc
        )
        new_pending_line = move.line_ids.filtered(
            lambda line, acc=pending_account: line.account_id == acc
        )
        (general_line + new_general_line).reconcile()
        self.write(
            {
                "xtd_discount_move_id": move.id,
                "xtd_effect_state": "discounted",
                "xtd_pending_effect_line_id": new_pending_line.id,
            }
        )

    def xtd_settle_effect(self):
        """Cancel the bank advance against the pending-effect control account.

        No cash moves here: the money already arrived at discount time. This
        just closes both the debt with the bank and the pending-effect
        control account, at the effect's maturity date.

        Runs each payment under its own savepoint: this is normally invoked
        from a daily cron over a batch of payments, and one payment with bad
        or legacy data (e.g. missing config, or created by an older version
        of this module) must not block the settlement of the rest.
        """
        for payment in self:
            if payment.xtd_effect_state != "discounted":
                continue
            if payment.xtd_settlement_move_id:
                continue
            try:
                with self.env.cr.savepoint():
                    payment._xtd_settle_effect_one()
            except Exception:
                _logger.exception(
                    "No se pudo liquidar el efecto del pago %s (id %s)",
                    payment.name,
                    payment.id,
                )
        return True

    def _xtd_settle_effect_one(self):
        self.ensure_one()
        mode = self.payment_order_id.payment_mode_id
        _pending_account, discounted_account = mode._xtd_effects_accounts_or_raise()
        pending_line = self.xtd_pending_effect_line_id
        if not pending_line:
            raise UserError(
                self.env._(
                    "El pago %s no tiene registrado el apunte de efecto"
                    " pendiente de vencer (dato de una versión anterior del"
                    " módulo); liquídalo manualmente.",
                    self.name,
                )
            )
        discount_line = self.xtd_discount_move_id.line_ids.filtered(
            lambda line, acc=discounted_account: line.account_id == acc
        )
        label = self.env._("Liquidación efecto %s", self.name)
        move = self.env["account.move"].create(
            {
                "journal_id": self.xtd_discount_move_id.journal_id.id,
                "date": fields.Date.context_today(self),
                "ref": label,
                "line_ids": [
                    Command.create(
                        {
                            "name": label,
                            "account_id": discounted_account.id,
                            "partner_id": self.partner_id.id,
                            "debit": self.amount,
                            "credit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": label,
                            "account_id": pending_line.account_id.id,
                            "partner_id": self.partner_id.id,
                            "debit": 0.0,
                            "credit": self.amount,
                        }
                    ),
                ],
            }
        )
        move._post()
        new_discount_line = move.line_ids.filtered(
            lambda line, acc=discounted_account: line.account_id == acc
        )
        new_pending_line = move.line_ids - new_discount_line
        (discount_line + new_discount_line).reconcile()
        (pending_line + new_pending_line).reconcile()
        self.write({"xtd_settlement_move_id": move.id, "xtd_effect_state": "settled"})

    def action_open_xtd_collection_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.xtd_collection_move_id.id,
            "target": "current",
        }

    def action_open_xtd_discount_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.xtd_discount_move_id.id,
            "target": "current",
        }

    def action_open_xtd_settlement_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.xtd_settlement_move_id.id,
            "target": "current",
        }

    def _xtd_effects_settle_cron(self):
        today = fields.Date.context_today(self)
        payments = self.search(
            [
                ("xtd_effect_state", "=", "discounted"),
                ("payment_line_ids.date", "<=", today),
            ]
        )
        payments.xtd_settle_effect()
