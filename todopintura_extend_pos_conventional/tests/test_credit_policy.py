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
        self.assertEqual(order.state, "linked")
        self.assertTrue(order.is_linked_to_sale)
        self.assertTrue(order.linked_sale_order_id)
        self.assertFalse(order.account_move)

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

