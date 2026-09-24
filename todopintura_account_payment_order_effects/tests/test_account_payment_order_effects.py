# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date, timedelta

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestXtdEffectsCommon


@tagged("-at_install", "post_install")
class TestAccountPaymentOrderEffects(TestXtdEffectsCommon):
    def test_upload_creates_discount_move_and_pending_effect(self):
        """At upload, an invoice NOT YET DUE must be reclassified from the
        general effects account (411000) to the 'pendientes de vencer'
        account (411001) -- never straight to the bank -- and a second,
        independent entry must record the bank's advance against the
        'efectos descontados' liability account."""
        due_date = date.today() + timedelta(days=20)
        invoice = self._create_customer_invoice(
            amount=100.0, invoice_date_due=due_date
        )
        order = self._create_and_upload_order(invoice)
        payment = order.payment_ids
        self.assertEqual(len(payment), 1)

        # 1) The invoice's own move: 430 (credit) / 411000 (debit), now
        # reconciled by the reclassification leg of the discount move.
        general_line = payment._seek_for_lines()[0]
        self.assertEqual(general_line.account_id, self.general_account)
        self.assertTrue(general_line.reconciled)
        # Reconciling the general/outstanding line against the reclass leg
        # marks the payment as matched, so the invoice moves straight to
        # "paid": once discounted, the invoice is off the sales ledger, even
        # though the company still carries the contingent debt with the
        # bank (520) until maturity.
        self.assertEqual(invoice.payment_state, "paid")

        # 2) The pending-effect line lives in 411001, still open.
        pending_line = payment.xtd_pending_effect_line_id
        self.assertEqual(pending_line.account_id, self.pending_account)
        self.assertFalse(pending_line.reconciled)
        self.assertEqual(pending_line.debit, 100.0)

        # 3) The discount (bank advance) move: bank (debit) / 520 (credit).
        self.assertEqual(payment.xtd_effect_state, "discounted")
        discount_move = payment.xtd_discount_move_id
        self.assertTrue(discount_move)
        self.assertEqual(discount_move.state, "posted")
        bank_line = discount_move.line_ids.filtered(
            lambda line: line.account_id == self.journal.default_account_id
        )
        discounted_line = discount_move.line_ids.filtered(
            lambda line: line.account_id == self.discounted_account
        )
        self.assertEqual(bank_line.debit, 100.0)
        self.assertEqual(discounted_line.credit, 100.0)
        self.assertFalse(discounted_line.reconciled)

        # No settlement yet.
        self.assertFalse(payment.xtd_settlement_move_id)

    def test_already_due_effect_goes_straight_to_bank(self):
        """An effect that is ALREADY due (or due today) at upload time skips
        the discount circuit entirely: the bridge account (411000) is closed
        directly against the bank (572), immediately -- no 411001, no 520,
        no waiting for the settlement cron, since the money is really being
        collected now."""
        invoice = self._create_customer_invoice(
            amount=40.0, invoice_date_due=date.today()
        )
        order = self._create_and_upload_order(invoice)
        payment = order.payment_ids

        self.assertEqual(payment.xtd_effect_state, "collected")
        self.assertFalse(payment.xtd_discount_move_id)
        self.assertFalse(payment.xtd_pending_effect_line_id)
        self.assertFalse(payment.xtd_settlement_move_id)

        general_line = payment._seek_for_lines()[0]
        self.assertEqual(general_line.account_id, self.general_account)
        self.assertTrue(general_line.reconciled)

        collection_move = payment.xtd_collection_move_id
        self.assertTrue(collection_move)
        self.assertEqual(collection_move.state, "posted")
        bank_line = collection_move.line_ids.filtered(
            lambda line: line.account_id == self.journal.default_account_id
        )
        self.assertEqual(bank_line.debit, 40.0)
        # No liability with the bank was ever created for this one.
        self.assertEqual(self._account_balance(self.discounted_account), 0.0)

    def test_disabled_mode_keeps_native_behaviour(self):
        """Sanity/regression check: payment modes that do NOT opt in must
        behave exactly as vanilla account_payment_order (no discount move,
        no xtd state), so existing payment modes are unaffected."""
        self.giro_mode.xtd_manage_effects_discount = False
        invoice = self._create_customer_invoice(amount=50.0)
        order = self._create_and_upload_order(invoice)
        payment = order.payment_ids
        self.assertFalse(payment.xtd_effect_state)
        self.assertFalse(payment.xtd_discount_move_id)

    def test_missing_discounted_account_raises(self):
        self.giro_mode.xtd_discounted_effects_account_id = False
        invoice = self._create_customer_invoice(amount=75.0)
        with self.assertRaises(UserError):
            self._create_and_upload_order(invoice)

    def test_missing_pending_account_raises(self):
        self.giro_mode.xtd_pending_effects_account_id = False
        invoice = self._create_customer_invoice(amount=75.0)
        with self.assertRaises(UserError):
            self._create_and_upload_order(invoice)

    def test_cron_does_not_settle_before_maturity(self):
        due_date = date.today() + timedelta(days=30)
        invoice = self._create_customer_invoice(
            amount=100.0, invoice_date_due=due_date
        )
        order = self._create_and_upload_order(invoice)
        payment = order.payment_ids
        self.assertEqual(payment.payment_line_date, due_date)

        self.env["account.payment"]._xtd_effects_settle_cron()
        payment.invalidate_recordset()
        self.assertEqual(payment.xtd_effect_state, "discounted")
        self.assertFalse(payment.xtd_settlement_move_id)

    def test_cron_settles_effect_at_maturity_with_no_cash_impact(self):
        """At maturity, both the bank debt (520) and the pending-effect
        control account (411001) must be closed by a wash entry that moves
        no cash, since the money already arrived at discount time."""
        due_date = date.today() + timedelta(days=15)
        invoice = self._create_customer_invoice(
            amount=200.0, invoice_date_due=due_date
        )
        order = self._create_and_upload_order(invoice)
        payment = order.payment_ids

        bank_balance_before = self._account_balance(self.journal.default_account_id)

        with freeze_time(due_date):
            self.env["account.payment"]._xtd_effects_settle_cron()
        payment.invalidate_recordset()

        self.assertEqual(payment.xtd_effect_state, "settled")
        settlement_move = payment.xtd_settlement_move_id
        self.assertTrue(settlement_move)
        self.assertEqual(settlement_move.state, "posted")

        # Both control accounts are now fully reconciled (net zero balance).
        self.assertEqual(self._account_balance(self.pending_account), 0.0)
        self.assertEqual(self._account_balance(self.discounted_account), 0.0)
        self.assertTrue(payment.xtd_pending_effect_line_id.reconciled)

        # The settlement itself moves no cash: the bank balance is unchanged
        # since the discount move already brought the money in.
        bank_balance_after = self._account_balance(self.journal.default_account_id)
        self.assertEqual(bank_balance_before, bank_balance_after)

    def test_two_invoices_are_tracked_independently(self):
        due_date_1 = date.today() + timedelta(days=10)
        due_date_2 = date.today() + timedelta(days=40)
        invoice_1 = self._create_customer_invoice(
            amount=60.0, invoice_date_due=due_date_1
        )
        invoice_2 = self._create_customer_invoice(
            amount=90.0, invoice_date_due=due_date_2
        )
        order = self._create_and_upload_order(invoice_1 + invoice_2)
        payments = order.payment_ids
        self.assertEqual(len(payments), 2)
        self.assertTrue(all(p.xtd_effect_state == "discounted" for p in payments))

        with freeze_time(due_date_1):
            self.env["account.payment"]._xtd_effects_settle_cron()
        payments.invalidate_recordset()
        payment_1 = payments.filtered(lambda p: p.amount == 60.0)
        payment_2 = payments.filtered(lambda p: p.amount == 90.0)
        self.assertEqual(payment_1.xtd_effect_state, "settled")
        self.assertEqual(payment_2.xtd_effect_state, "discounted")

    def _account_balance(self, account):
        lines = self.env["account.move.line"].search(
            [("account_id", "=", account.id), ("parent_state", "=", "posted")]
        )
        return sum(lines.mapped("balance"))
