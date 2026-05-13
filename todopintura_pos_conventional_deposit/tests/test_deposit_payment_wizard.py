from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestDepositPaymentWizard(PosConventionalTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_payment_method = cls.card_pm
        config_vals = {
            "journal_id": cls.invoice_journal.id,
            "invoice_journal_id": cls.invoice_journal.id,
        }
        if "l10n_es_simplified_invoice_journal_id" in cls.pos_config._fields:
            config_vals["l10n_es_simplified_invoice_journal_id"] = cls.invoice_journal.id
        cls.pos_config.write(config_vals)

    def _create_deposit_order(self, partner=None, session=None):
        partner = partner or self.partner
        session = session or self._open_session()
        order = self._make_draft_order(session, partner=partner)
        self._add_line(order, self.product)
        current_location = order.config_id.picking_type_id.default_location_src_id
        partner.commercial_partner_id.write(
            {
                "pos_conventional_sale_mode": "deposit",
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )
        order.action_pay_deposit()
        return order

    def test_action_open_deposit_payment_wizard_returns_modal(self):
        session = self._open_session()
        action = self.env["pos.order"].with_context(default_session_id=session.id).action_open_deposit_payment_wizard()
        self.assertEqual(action["res_model"], "pos.deposit.payment.wizard")
        self.assertEqual(action["target"], "new")
        self.assertTrue(action["res_id"])
        self.assertEqual(action["context"]["default_session_id"], session.id)
        self.assertEqual(action["context"]["dialog_size"], "medium")
        wizard = self.env["pos.deposit.payment.wizard"].browse(action["res_id"])
        self.assertEqual(wizard.session_id, session)
        self.assertNotIn("lines", dict(wizard._fields["step"].selection))
        self.assertNotIn("deposit_line_ids", wizard._fields)

    def test_partner_onchange_loads_only_deposit_orders_without_invoice(self):
        order = self._create_deposit_order()
        other_session = self._open_session(self._make_no_cash_control_config())
        other_order = self._make_draft_order(other_session, partner=self.partner)
        self._add_line(other_order, self.product)

        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": order.session_id.id,
                "partner_id": self.partner.id,
            }
        )
        wizard._onchange_partner_id()

        self.assertIn(order, wizard.deposit_order_line_ids.mapped("order_id"))
        self.assertNotIn(other_order, wizard.deposit_order_line_ids.mapped("order_id"))

    def test_eligible_partners_use_commercial_partner_and_ignore_customer_rank(self):
        commercial_partner = self.env["res.partner"].create(
            {"name": "Cliente comercial depósito"}
        )
        contact_partner = self.env["res.partner"].create(
            {
                "name": "Contacto depósito",
                "parent_id": commercial_partner.id,
                "type": "contact",
            }
        )
        order = self._create_deposit_order(partner=contact_partner)
        commercial_partner.invalidate_recordset(["customer_rank"])
        self.assertEqual(commercial_partner.customer_rank, 0)

        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": order.session_id.id,
                "partner_id": commercial_partner.id,
            }
        )
        wizard._compute_eligible_partner_ids()
        wizard._onchange_partner_id()

        self.assertIn(commercial_partner, wizard.eligible_partner_ids)
        self.assertIn(order, wizard.deposit_order_line_ids.mapped("order_id"))

    def test_selected_amounts_are_computed_from_selected_orders(self):
        session = self._open_session()
        order_1 = self._create_deposit_order(session=session)
        order_2 = self._create_deposit_order(session=session)

        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": session.id,
                "partner_id": self.partner.id,
            }
        )
        wizard._onchange_partner_id()

        selected_lines = wizard.deposit_order_line_ids.filtered(
            lambda line: line.order_id in (order_1 | order_2)
        )
        selected_lines.selected = True
        wizard._compute_selected_amounts()

        self.assertEqual(wizard.selected_order_count, 2)
        self.assertEqual(wizard.amount_total, order_1.amount_total + order_2.amount_total)

    def test_wizard_step_navigation_keeps_selected_orders(self):
        session = self._open_session()
        order_1 = self._create_deposit_order(session=session)
        order_2 = self._create_deposit_order(session=session)

        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": session.id,
                "partner_id": self.partner.id,
            }
        )
        wizard._onchange_partner_id()
        for line in wizard.deposit_order_line_ids:
            line.selected = line.order_id in (order_1 | order_2)

        action_payment = wizard.action_go_to_payment_step()
        self.assertEqual(wizard.step, "payment")
        self.assertEqual(action_payment["context"]["dialog_size"], "medium")
        self.assertEqual(wizard.selected_order_count, 2)

        wizard.action_back_to_order_step()
        self.assertEqual(wizard.step, "orders")
        self.assertEqual(wizard.selected_order_count, 2)

    def test_action_confirm_creates_single_invoice_for_selected_orders(self):
        session = self._open_session()
        order_1 = self._create_deposit_order(session=session)
        order_2 = self._create_deposit_order(session=session)

        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": order_1.session_id.id,
                "partner_id": self.partner.id,
            }
        )
        wizard._onchange_partner_id()
        for line in wizard.deposit_order_line_ids:
            line.selected = line.order_id in (order_1 | order_2)
        wizard.write(
            {
                "payment_line_ids": [
                    (5, 0, 0),
                    (0, 0, {"payment_method_id": self.cash_pm.id, "amount": order_1.amount_total}),
                    (0, 0, {"payment_method_id": self.bank_payment_method.id, "amount": order_2.amount_total}),
                ]
            }
        )

        action = wizard.action_confirm()

        self.assertTrue(order_1.account_move)
        self.assertEqual(order_1.account_move, order_2.account_move)
        self.assertEqual(order_1.state, "done")
        self.assertEqual(order_2.state, "done")
        self.assertEqual(order_1.account_move.amount_residual, 0.0)
        self.assertIn(order_1.account_move.payment_state, {"paid", "in_payment"})
        self.assertEqual(action.get("tag"), "pos_conventional_print_receipt_window")
        self.assertEqual(action.get("params", {}).get("move_id"), order_1.account_move.id)
        self.assertTrue(action.get("params", {}).get("report_autoprints"))
        self.assertIn(
            "/report/html/pos_conventional_receipt_custom.report_factura_simplificada_80mm/",
            action.get("params", {}).get("url", ""),
        )
        self.assertFalse(action.get("params", {}).get("clear_breadcrumbs", True))
        self.assertEqual(action.get("params", {}).get("next_action", {}).get("res_model"), "account.move")
        self.assertEqual(action.get("params", {}).get("next_action", {}).get("res_id"), order_1.account_move.id)
        self.assertEqual(action.get("params", {}).get("next_action", {}).get("target"), "current")

    def test_action_confirm_uses_pos_invoice_journal_for_deposits(self):
        session = self._open_session()
        order = self._create_deposit_order(session=session)
        config = session.config_id
        pos_sale_journal = self.env["account.journal"].create(
            {
                "name": "POS Depositos Test",
                "code": "PDTST",
                "type": "sale",
                "company_id": config.company_id.id,
            }
        )
        config.write(
            {
                "journal_id": pos_sale_journal.id,
                "invoice_journal_id": self.invoice_journal.id,
                "l10n_es_simplified_invoice_journal_id": self.invoice_journal.id,
            }
        )

        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": session.id,
                "partner_id": self.partner.id,
            }
        )
        wizard._onchange_partner_id()
        wizard.deposit_order_line_ids.selected = True
        wizard.write(
            {
                "payment_line_ids": [
                    (5, 0, 0),
                    (0, 0, {"payment_method_id": self.cash_pm.id, "amount": order.amount_total}),
                ]
            }
        )

        wizard.action_confirm()

        self.assertEqual(order.account_move.journal_id, pos_sale_journal)

    def test_action_confirm_blocks_generic_sales_journal_for_deposits(self):
        session = self._open_session()
        order = self._create_deposit_order(session=session)
        config = session.config_id
        general_pos_journal = self.env["account.journal"].create(
            {
                "name": "POS General Depositos Test",
                "code": "PGTST",
                "type": "general",
                "company_id": config.company_id.id,
            }
        )
        config.write(
            {
                "journal_id": general_pos_journal.id,
                "invoice_journal_id": self.invoice_journal.id,
                "l10n_es_simplified_invoice_journal_id": self.invoice_journal.id,
            }
        )

        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": session.id,
                "partner_id": self.partner.id,
            }
        )
        wizard._onchange_partner_id()
        wizard.deposit_order_line_ids.selected = True
        wizard.write(
            {
                "payment_line_ids": [
                    (5, 0, 0),
                    (0, 0, {"payment_method_id": self.cash_pm.id, "amount": order.amount_total}),
                ]
            }
        )

        with self.assertRaises(UserError):
            wizard.action_confirm()

        self.assertFalse(order.account_move)
        self.assertEqual(order.state, "deposit")

    def test_action_confirm_allows_cash_change_and_only_registers_due_amount(self):
        order = self._create_deposit_order()
        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": order.session_id.id,
                "partner_id": self.partner.id,
            }
        )
        wizard._onchange_partner_id()
        wizard.deposit_order_line_ids.selected = True
        wizard.write(
            {
                "payment_line_ids": [
                    (5, 0, 0),
                    (0, 0, {"payment_method_id": self.cash_pm.id, "amount": order.amount_total + 10.0}),
                ]
            }
        )
        wizard.invalidate_recordset(["amount_due", "amount_change", "amount_paid_total"])

        self.assertGreater(wizard.amount_change, 0.0)
        self.assertEqual(wizard.amount_due, 0.0)

        action = wizard.action_confirm()

        self.assertEqual(order.account_move.amount_residual, 0.0)
        self.assertIn(order.account_move.payment_state, {"paid", "in_payment"})
        self.assertEqual(action.get("tag"), "pos_conventional_print_receipt_window")
        self.assertEqual(action.get("params", {}).get("move_id"), order.account_move.id)
        self.assertTrue(action.get("params", {}).get("report_autoprints"))
        self.assertIn(
            "/report/html/pos_conventional_receipt_custom.report_factura_simplificada_80mm/",
            action.get("params", {}).get("url", ""),
        )
        self.assertFalse(action.get("params", {}).get("clear_breadcrumbs", True))
        self.assertEqual(action.get("params", {}).get("next_action", {}).get("target"), "current")

    def test_action_confirm_rejects_non_cash_overpayment(self):
        order = self._create_deposit_order()
        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": order.session_id.id,
                "partner_id": self.partner.id,
            }
        )
        wizard._onchange_partner_id()
        wizard.deposit_order_line_ids.selected = True
        wizard.write(
            {
                "payment_line_ids": [
                    (5, 0, 0),
                    (0, 0, {"payment_method_id": self.bank_payment_method.id, "amount": order.amount_total + 5.0}),
                ]
            }
        )

        with self.assertRaises(UserError):
            wizard.action_confirm()

        self.assertFalse(order.account_move)
        self.assertEqual(order.state, "deposit")


