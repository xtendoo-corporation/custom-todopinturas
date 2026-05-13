from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestDepositOrder(PosConventionalTestCommon):

    def test_module_keeps_only_full_deposit_flow(self):
        state_values = dict(self.env["pos.order"]._fields["state"].selection)
        self.assertIn("deposit", state_values)
        self.assertNotIn("deposit_partial", state_values)
        self.assertNotIn("is_deposit_paid", self.env["pos.order.line"]._fields)

    def _prepare_deposit_order(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order, self.product)
        return order

    def _set_partner_deposit_mode(self, locations=None):
        values = {
            "pos_conventional_sale_mode": "deposit",
        }
        if locations is not None:
            values["pos_credit_location_ids"] = [(6, 0, locations.ids)]
        self.partner.commercial_partner_id.write(values)

    def test_action_pay_deposit_creates_picking_and_sets_state(self):
        order = self._prepare_deposit_order()
        current_location = order.config_id.picking_type_id.default_location_src_id
        self._set_partner_deposit_mode(current_location)

        action = order.action_pay_deposit()

        self.assertEqual(order.state, "deposit")
        self.assertFalse(order.linked_sale_order_id)
        self.assertFalse(order.account_move)
        self.assertTrue(order.picking_ids)
        self.assertIsInstance(action, dict)
        self.assertFalse(action.get("res_id"))
        self.assertTrue(all(picking.pos_order_id == order for picking in order.picking_ids))
        self.assertTrue(all(picking.location_dest_id.name == "Depósito" for picking in order.picking_ids))
        self.assertTrue(all(picking.location_dest_id.usage == "transit" for picking in order.picking_ids))

    def test_action_pay_deposit_reuses_same_virtual_location(self):
        order = self._prepare_deposit_order()
        current_location = order.config_id.picking_type_id.default_location_src_id
        self._set_partner_deposit_mode(current_location)

        first_location = order._get_or_create_conventional_deposit_location()
        second_location = order._get_or_create_conventional_deposit_location()

        self.assertEqual(first_location, second_location)
        self.assertEqual(first_location.name, "Depósito")
        self.assertEqual(first_location.usage, "transit")

    def test_action_pay_deposit_requires_partner_in_deposit_mode(self):
        order = self._prepare_deposit_order()
        self.partner.commercial_partner_id.write({"pos_conventional_sale_mode": "credit"})

        with self.assertRaises(UserError):
            order.action_pay_deposit()

    def test_action_pay_deposit_blocks_disallowed_store(self):
        order = self._prepare_deposit_order()
        current_location = order.config_id.picking_type_id.default_location_src_id
        other_location = self.env["stock.location"].search(
            [("usage", "=", "internal"), ("id", "!=", current_location.id)],
            limit=1,
        )
        if not other_location:
            self.skipTest("No hay una segunda ubicación interna para validar la restricción de depósito.")

        self._set_partner_deposit_mode(other_location)

        with self.assertRaises(UserError):
            order.action_pay_deposit()

    def test_compute_partner_deposit_policy_enables_button_only_when_allowed(self):
        order = self._prepare_deposit_order()
        current_location = order.config_id.picking_type_id.default_location_src_id
        self._set_partner_deposit_mode(current_location)

        order._compute_partner_deposit_policy()
        self.assertTrue(order.partner_deposit_enabled)
        self.assertTrue(order.partner_deposit_available)
        self.assertTrue(order.show_deposit_button)

        self._add_payment(order, self.cash_pm, order.amount_total / 2.0)
        order._compute_partner_deposit_policy()
        self.assertFalse(order.show_deposit_button)

