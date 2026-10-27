from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestCreditAndDeposit(PosConventionalTestCommon):
    """Crédito y depósito son independientes: se prueban solos, juntos y ninguno."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "pos_can_edit_price" in cls.env.user._fields:
            cls.env.user.pos_can_edit_price = True
        cls.pay_later_pm = cls.env["pos.payment.method"].create(
            {
                "name": "Cuenta cliente crédito+depósito test",
                "journal_id": cls.invoice_journal.id,
            }
        )
        cls.pos_config.write({"payment_method_ids": [(4, cls.pay_later_pm.id)]})
        cls.Partner = cls.env["res.partner"]
        cls.store = cls.env["stock.location"].search(
            [("usage", "=", "internal")], limit=1
        )
        cls.store_ids = [(6, 0, cls.store.ids)]
        cls.partner_credit = cls.Partner.create(
            {"name": "Cliente solo crédito", "pos_credit_sale_enabled": True}
        )
        cls.partner_deposit = cls.Partner.create(
            {
                "name": "Cliente solo depósito",
                "pos_deposit_sale_enabled": True,
                "pos_credit_location_ids": cls.store_ids,
            }
        )
        cls.partner_both = cls.Partner.create(
            {
                "name": "Cliente crédito y depósito",
                "pos_credit_sale_enabled": True,
                "pos_deposit_sale_enabled": True,
                "pos_credit_location_ids": cls.store_ids,
            }
        )
        cls.partner_none = cls.Partner.create({"name": "Cliente sin crédito ni depósito"})

    def _order(self, partner, session=None):
        session = session or self._open_session()
        order = self._make_draft_order(session, partner=partner)
        self._add_line(order, self.product)
        return order

    def _allow_current_store(self, order, partner):
        location = order.config_id.picking_type_id.default_location_src_id
        partner.write({"pos_credit_location_ids": [(6, 0, location.ids)]})
        return location

    def _credit_policy(self, order):
        return order._get_conventional_credit_policy_data(
            amount=order.amount_total, payment_method=self.pay_later_pm
        )

    # --- flags y selector resumen -------------------------------------------------

    def test_flags_are_independent_and_mode_follows(self):
        partner = self.Partner.create(
            {"name": "Flags", "pos_credit_location_ids": self.store_ids}
        )
        self.assertEqual(partner.pos_conventional_sale_mode, "none")
        partner.pos_credit_sale_enabled = True
        self.assertEqual(partner.pos_conventional_sale_mode, "credit")
        partner.pos_deposit_sale_enabled = True
        self.assertTrue(partner.pos_credit_sale_enabled)
        self.assertEqual(partner.pos_conventional_sale_mode, "both")
        partner.pos_credit_sale_enabled = False
        self.assertTrue(partner.pos_deposit_sale_enabled)
        self.assertEqual(partner.pos_conventional_sale_mode, "deposit")
        partner.pos_deposit_sale_enabled = False
        self.assertEqual(partner.pos_conventional_sale_mode, "none")

    def test_deposit_requires_store(self):
        with self.assertRaises(ValidationError):
            self.Partner.create(
                {"name": "Depósito sin tienda", "pos_deposit_sale_enabled": True}
            )
        partner = self.Partner.create({"name": "Sin depósito"})
        with self.assertRaises(ValidationError):
            partner.pos_deposit_sale_enabled = True
        partner.write(
            {
                "pos_deposit_sale_enabled": True,
                "pos_credit_location_ids": self.store_ids,
            }
        )
        with self.assertRaises(ValidationError):
            partner.pos_credit_location_ids = False

    def test_legacy_mode_both_sets_both_flags(self):
        partner = self.Partner.create(
            {
                "name": "Modo both",
                "pos_conventional_sale_mode": "both",
                "pos_credit_location_ids": self.store_ids,
            }
        )
        self.assertTrue(partner.pos_credit_sale_enabled)
        self.assertTrue(partner.pos_deposit_sale_enabled)

    def test_fixture_modes(self):
        self.assertEqual(self.partner_credit.pos_conventional_sale_mode, "credit")
        self.assertEqual(self.partner_deposit.pos_conventional_sale_mode, "deposit")
        self.assertEqual(self.partner_both.pos_conventional_sale_mode, "both")
        self.assertEqual(self.partner_none.pos_conventional_sale_mode, "none")

    # --- solo crédito -----------------------------------------------------------

    def test_credit_only_allows_credit_and_blocks_deposit(self):
        order = self._order(self.partner_credit)
        self.assertTrue(self._credit_policy(order)["credit_sale_allowed"])
        policy = order._get_conventional_deposit_policy_data()
        self.assertFalse(policy["deposit_enabled"])
        self.assertFalse(policy["deposit_available"])
        with self.assertRaises(UserError):
            order.action_pay_deposit()

    def test_credit_only_pay_later_creates_linked_sale(self):
        order = self._order(self.partner_credit)
        order.action_pos_convention_pay_with_method(self.pay_later_pm.id)
        self.assertEqual(order.state, "linked")
        self.assertTrue(order.linked_sale_order_id)

    # --- solo depósito ----------------------------------------------------------

    def test_deposit_only_allows_deposit_and_blocks_credit(self):
        order = self._order(self.partner_deposit)
        self._allow_current_store(order, self.partner_deposit)
        policy = self._credit_policy(order)
        self.assertFalse(policy["credit_sale_allowed"])
        self.assertIn("depósito", policy["error_message"])
        self.assertTrue(order._get_conventional_deposit_policy_data()["deposit_available"])
        order.action_pay_deposit()
        self.assertEqual(order.state, "deposit")
        self.assertTrue(order.picking_ids)

    # --- crédito y depósito a la vez -------------------------------------------

    def test_both_allows_credit_and_deposit_policies(self):
        order = self._order(self.partner_both)
        self._allow_current_store(order, self.partner_both)
        self.assertTrue(self._credit_policy(order)["credit_sale_allowed"])
        self.assertTrue(order._get_conventional_deposit_policy_data()["deposit_available"])
        order._compute_partner_deposit_policy()
        self.assertTrue(order.partner_deposit_enabled)
        self.assertTrue(order.show_deposit_button)

    def test_both_credit_is_not_restricted_by_deposit_stores(self):
        order = self._order(self.partner_both)
        current = order.config_id.picking_type_id.default_location_src_id
        other = self.env["stock.location"].search(
            [("usage", "=", "internal"), ("id", "!=", current.id)], limit=1
        )
        if not other:
            self.skipTest("No hay una segunda ubicación interna.")
        self.partner_both.write({"pos_credit_location_ids": [(6, 0, other.ids)]})
        # El crédito sigue funcionando en cualquier tienda...
        policy = self._credit_policy(order)
        self.assertTrue(policy["credit_sale_allowed"])
        self.assertTrue(policy["location_allowed"])
        # ...pero el depósito solo en las tiendas indicadas.
        self.assertFalse(order._get_conventional_deposit_policy_data()["deposit_available"])
        with self.assertRaises(UserError):
            order.action_pay_deposit()

    def test_both_can_do_deposit_and_credit_in_same_session(self):
        session = self._open_session()
        deposit_order = self._order(self.partner_both, session)
        self._allow_current_store(deposit_order, self.partner_both)
        deposit_order.action_pay_deposit()
        self.assertEqual(deposit_order.state, "deposit")

        credit_order = self._order(self.partner_both, session)
        credit_order.action_pos_convention_pay_with_method(self.pay_later_pm.id)
        self.assertEqual(credit_order.state, "linked")
        self.assertTrue(credit_order.linked_sale_order_id)
        # El pedido en depósito no se ve afectado por la venta a crédito posterior.
        self.assertEqual(deposit_order.state, "deposit")

    # --- ninguno ------------------------------------------------------------------

    def test_none_blocks_credit_and_deposit(self):
        order = self._order(self.partner_none)
        self.assertFalse(self._credit_policy(order)["credit_sale_allowed"])
        self.assertFalse(order._get_conventional_deposit_policy_data()["deposit_enabled"])
        with self.assertRaises(UserError):
            order.action_pay_deposit()
