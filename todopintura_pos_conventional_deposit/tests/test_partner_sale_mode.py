from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestPartnerSaleMode(PosConventionalTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pay_later_pm = cls.env["pos.payment.method"].create(
            {
                "name": "Cuenta cliente depósito test",
                "journal_id": cls.invoice_journal.id,
            }
        )
        cls.pos_config.write({"payment_method_ids": [(4, cls.pay_later_pm.id)]})

    def test_credit_mode_allows_credit_in_any_store(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        current_location = order.config_id.picking_type_id.default_location_src_id
        other_location = self.env["stock.location"].search(
            [("usage", "=", "internal"), ("id", "!=", current_location.id)],
            limit=1,
        )
        if not other_location:
            self.skipTest("No hay una segunda ubicación interna para validar tiendas distintas.")

        self.partner.commercial_partner_id.write(
            {
                "pos_conventional_sale_mode": "credit",
                "pos_credit_location_ids": [(6, 0, [other_location.id])],
            }
        )

        policy = order._get_conventional_credit_policy_data(
            amount=order.amount_total,
            payment_method=self.pay_later_pm,
        )

        self.assertEqual(self.partner.commercial_partner_id._get_pos_conventional_sale_mode(), "credit")
        self.assertTrue(self.partner.commercial_partner_id.pos_credit_sale_enabled)
        self.assertFalse(self.partner.commercial_partner_id._get_conventional_credit_locations())
        self.assertTrue(policy["credit_sale_allowed"])
        self.assertTrue(policy["location_allowed"])
        self.assertFalse(policy["allowed_location_names"])

    def test_deposit_mode_blocks_credit_sale_and_keeps_allowed_locations(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        current_location = order.config_id.picking_type_id.default_location_src_id

        self.partner.commercial_partner_id.write(
            {
                "pos_conventional_sale_mode": "deposit",
                "pos_credit_location_ids": [(6, 0, [current_location.id])],
            }
        )

        policy = order._get_conventional_credit_policy_data(
            amount=order.amount_total,
            payment_method=self.pay_later_pm,
        )

        self.assertEqual(self.partner.commercial_partner_id._get_pos_conventional_sale_mode(), "deposit")
        self.assertFalse(self.partner.commercial_partner_id.pos_credit_sale_enabled)
        self.assertEqual(
            self.partner.commercial_partner_id._get_conventional_credit_locations(),
            current_location,
        )
        self.assertFalse(policy["credit_sale_allowed"])
        self.assertIn("depósito", policy["error_message"])

    def test_empty_mode_blocks_credit_sale(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        self.partner.commercial_partner_id.write(
            {
                "pos_conventional_sale_mode": "none",
            }
        )

        policy = order._get_conventional_credit_policy_data(
            amount=order.amount_total,
            payment_method=self.pay_later_pm,
        )

        self.assertEqual(self.partner.commercial_partner_id._get_pos_conventional_sale_mode(), "none")
        self.assertFalse(self.partner.commercial_partner_id.pos_credit_sale_enabled)
        self.assertFalse(policy["credit_sale_allowed"])

    def test_legacy_boolean_write_is_mapped_to_sale_mode(self):
        self.partner.commercial_partner_id.write({"pos_credit_sale_enabled": True})
        self.assertEqual(self.partner.commercial_partner_id.pos_conventional_sale_mode, "credit")

        self.partner.commercial_partner_id.write({"pos_credit_sale_enabled": False})
        self.assertEqual(self.partner.commercial_partner_id.pos_conventional_sale_mode, "none")

    def test_selection_value_has_priority_when_both_fields_are_written(self):
        self.partner.commercial_partner_id.write(
            {
                "pos_conventional_sale_mode": "deposit",
                "pos_credit_sale_enabled": True,
            }
        )

        self.assertEqual(self.partner.commercial_partner_id.pos_conventional_sale_mode, "deposit")
        self.assertFalse(self.partner.commercial_partner_id.pos_credit_sale_enabled)

    def test_legacy_boolean_create_is_mapped_to_sale_mode(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Cliente legado depósito",
                "pos_credit_sale_enabled": True,
            }
        )

        self.assertEqual(partner.pos_conventional_sale_mode, "credit")

