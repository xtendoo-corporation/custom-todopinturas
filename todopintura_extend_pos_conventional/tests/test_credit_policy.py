from odoo import fields
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestConventionalCreditPolicy(PosConventionalTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pay_later_pm = cls.env["pos.payment.method"].create(
            {
                "name": "Cuenta cliente test",
                "journal_id": cls.invoice_journal.id,
            }
        )
        cls.pos_config.write({"payment_method_ids": [(4, cls.pay_later_pm.id)]})

    def _create_open_invoice(self, partner, amount):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "journal_id": self.invoice_journal.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "quantity": 1.0,
                            "price_unit": amount,
                        },
                    )
                ],
            }
        )
        move.action_post()
        return move

    def test_credit_policy_accepts_any_allowed_location(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        current_location = order.config_id.picking_type_id.default_location_src_id
        other_location = self.env["stock.location"].search(
            [("usage", "=", "internal"), ("id", "!=", current_location.id)],
            limit=1,
        )
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [loc.id for loc in (current_location | other_location)])],
            }
        )

        policy = order._get_conventional_credit_policy_data(
            amount=order.amount_total,
            payment_method=self.pay_later_pm,
        )

        self.assertTrue(policy["credit_sale_allowed"])
        self.assertTrue(policy["location_allowed"])
        self.assertIn(current_location.display_name, policy["allowed_location_names"])

    def test_order_exposes_cashier_credit_warning_when_credit_is_available(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        current_location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )

        order._compute_partner_credit_policy()

        self.assertTrue(order.partner_credit_available)
        self.assertIn("Pago Cuenta de cliente", order.partner_credit_cashier_warning)

    def test_credit_policy_blocks_disallowed_location(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        current_location = order.config_id.picking_type_id.default_location_src_id
        other_location = self.env["stock.location"].search(
            [("usage", "=", "internal"), ("id", "!=", current_location.id)],
            limit=1,
        )
        if not other_location:
            self.skipTest("No hay una segunda ubicación interna para validar la restricción.")

        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [other_location.id])],
            }
        )

        policy = order._get_conventional_credit_policy_data(
            amount=order.amount_total,
            payment_method=self.pay_later_pm,
        )

        self.assertFalse(policy["location_allowed"])
        self.assertIn(other_location.display_name, policy["location_error"])
        self.assertIn(current_location.display_name, policy["location_error"])

    def test_credit_policy_requires_override_when_limit_is_exceeded(self):
        self._create_open_invoice(self.partner, 90.0)
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "use_partner_credit_limit": True,
                "credit_limit": 100.0,
            }
        )

        policy = order._get_conventional_credit_policy_data(
            amount=order.amount_total,
            payment_method=self.pay_later_pm,
        )

        self.assertTrue(policy["limit_exceeded"])
        self.assertTrue(policy["needs_limit_override"])
        self.assertGreater(policy["total_after"], policy["credit_limit"])

    def test_draft_order_with_pay_later_payment_can_leave(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        self._add_payment(order, self.pay_later_pm, order.amount_total)

        self.assertTrue(order.has_draft_pay_later_payment())

    def test_draft_order_without_pay_later_payment_keeps_restriction(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        self._add_payment(order, self.cash_pm, order.amount_total / 2.0)

        self.assertFalse(order.has_draft_pay_later_payment())

    def test_action_pos_convention_pay_with_pay_later_processes_order(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
            }
        )

        action = order.action_pos_convention_pay_with_method(self.pay_later_pm.id)

        self.assertTrue(action)
        self.assertNotEqual(action.get("tag"), "pos_conventional_print_iframe")
        self.assertEqual(order.state, "linked")
        self.assertTrue(order.is_linked_to_sale)
        self.assertTrue(order.linked_sale_order_id)
        self.assertFalse(order.account_move)
        self.assertFalse(order.to_invoice)

    def test_pos_make_payment_pay_later_creates_linked_sale_without_invoice(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
            }
        )

        wizard = self.env["pos.make.payment"].with_context(active_id=order.id).create(
            {
                "amount": order.amount_total,
                "payment_method_id": self.pay_later_pm.id,
            }
        )
        action = wizard.check()

        self.assertTrue(action)
        self.assertNotEqual(action.get("tag"), "pos_conventional_print_iframe")
        self.assertEqual(order.state, "linked")
        self.assertTrue(order.is_linked_to_sale)
        self.assertTrue(order.linked_sale_order_id)
        self.assertFalse(order.account_move)

    def test_payment_popup_pay_later_creates_linked_sale_without_invoice(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
            }
        )

        wizard = self.env["pos.make.payment.wizard"].with_context(active_id=order.id).create(
            {
                "order_id": order.id,
                "payment_method_id": self.pay_later_pm.id,
                "amount_tendered": order.amount_total,
            }
        )
        action = wizard.action_add_payment()

        self.assertTrue(action)
        self.assertNotEqual(action.get("tag"), "pos_conventional_print_iframe")
        self.assertEqual(order.state, "linked")
        self.assertTrue(order.is_linked_to_sale)
        self.assertTrue(order.linked_sale_order_id)
        self.assertFalse(order.account_move)

    def test_partner_selection_warning_action_opens_confirmation_wizard(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        current_location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )

        action = order.action_open_partner_credit_cashier_warning()

        self.assertEqual(
            action["res_model"],
            "pos.conventional.credit.cashier.warning.wizard",
        )
        warning_wizard = self.env[
            "pos.conventional.credit.cashier.warning.wizard"
        ].with_context(action["context"]).create({})
        continue_action = warning_wizard.action_continue()

        self.assertEqual(continue_action["type"], "ir.actions.act_window_close")

    def test_partner_selection_warning_cancel_restores_previous_partner(self):
        session = self._open_session()
        previous_partner = self.env["res.partner"].create(
            {"name": "Cliente previo POS", "customer_rank": 1}
        )
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        current_location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )

        action = order.action_open_partner_credit_cashier_warning(
            previous_partner_id=previous_partner.id,
        )

        warning_wizard = self.env[
            "pos.conventional.credit.cashier.warning.wizard"
        ].with_context(action["context"]).create({})
        cancel_action = warning_wizard.action_cancel()
        order.invalidate_recordset(["partner_id"])

        self.assertEqual(cancel_action["tag"], "reload")
        self.assertEqual(order.partner_id, previous_partner)

    def test_card_payment_keeps_receipt_printing_when_customer_has_credit(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        self.pos_config.write({"iface_print_auto": True})
        current_location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )

        action = order.action_pos_convention_pay_with_method(self.card_pm.id)

        self.assertEqual(action["tag"], "pos_conventional_print_receipt_window")
        self.assertTrue(action["params"]["move_id"])
        self.assertIn("/report/html/pos_conventional_receipt_custom.report_factura_simplificada_80mm/", action["params"]["url"])
        self.assertEqual(action["params"]["order_id"], order.id)

    def test_card_payment_uses_a4_invoice_report_when_flag_is_enabled(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        order.write({"is_a4_invoice": True})
        self.pos_config.write({"iface_print_auto": True})
        current_location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )

        action = order.action_pos_convention_pay_with_method(self.card_pm.id)

        self.assertEqual(action["tag"], "pos_conventional_print_receipt_window")
        self.assertTrue(action["params"]["is_a4_invoice"])
        self.assertFalse(action["params"]["report_autoprints"])
        self.assertIn(
            "/report/html/account.report_invoice_with_payments/",
            action["params"]["url"],
        )

    def test_cash_payment_validation_keeps_receipt_printing_when_customer_has_credit(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        self.pos_config.write({"iface_print_auto": True})
        current_location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )

        cash_action = order.action_pay_cash()

        self.assertEqual(cash_action["res_model"], "pos.make.payment.wizard")
        wizard = self.env["pos.make.payment.wizard"].with_context(
            active_id=order.id,
            cash_only=True,
            cash_quick_mode=True,
            default_payment_method_id=self.cash_pm.id,
            default_amount_tendered=order.amount_total,
        ).create(
            {
                "order_id": order.id,
                "payment_method_id": self.cash_pm.id,
                "amount_tendered": order.amount_total,
            }
        )

        action = wizard.action_validate()

        self.assertEqual(action["tag"], "pos_conventional_print_receipt_window")
        self.assertTrue(action["params"]["move_id"])
        self.assertIn("/report/html/pos_conventional_receipt_custom.report_factura_simplificada_80mm/", action["params"]["url"])
        order.invalidate_recordset(["payment_ids", "amount_paid", "state"])
        self.assertGreaterEqual(order.amount_paid, order.amount_total)
        self.assertIn(order.state, ("paid", "done"))

    def test_cash_payment_validation_uses_a4_invoice_report_when_flag_is_enabled(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        order.write({"is_a4_invoice": True})
        self.pos_config.write({"iface_print_auto": True})
        current_location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_credit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )

        wizard = self.env["pos.make.payment.wizard"].with_context(
            active_id=order.id,
            cash_only=True,
            cash_quick_mode=True,
            default_payment_method_id=self.cash_pm.id,
            default_amount_tendered=order.amount_total,
        ).create(
            {
                "order_id": order.id,
                "payment_method_id": self.cash_pm.id,
                "amount_tendered": order.amount_total,
            }
        )

        action = wizard.action_validate()

        self.assertEqual(action["tag"], "pos_conventional_print_receipt_window")
        self.assertTrue(action["params"]["is_a4_invoice"])
        self.assertFalse(action["params"]["report_autoprints"])
        self.assertIn(
            "/report/html/account.report_invoice_with_payments/",
            action["params"]["url"],
        )

    def test_conventional_config_exposes_source_location(self):
        self.assertTrue(self.pos_config.pos_non_touch)
        self.assertEqual(
            self.pos_config.conventional_source_location_id,
            self.pos_config.picking_type_id.default_location_src_id,
        )
        self.pos_config._ensure_conventional_source_location()

    def test_settings_expose_conventional_source_location(self):
        settings = self.env["res.config.settings"].create(
            {
                "pos_config_id": self.pos_config.id,
            }
        )

        self.assertEqual(
            settings.pos_conventional_source_location_id,
            self.pos_config.conventional_source_location_id,
        )

