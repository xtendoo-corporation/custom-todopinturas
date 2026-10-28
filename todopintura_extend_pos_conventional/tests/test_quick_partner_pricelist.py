from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestQuickPartnerPricelist(TransactionCase):
    def test_flag_default_false(self):
        pl = self.env["product.pricelist"].create({"name": "PL test"})
        self.assertFalse(pl.pos_quick_partner_selectable)

    def test_wizard_pricelist_restricted(self):
        Pricelist = self.env["product.pricelist"]
        denied = Pricelist.create({"name": "PL no permitida"})
        wizard_model = self.env["pos.conventional.quick.partner.wizard"]
        order = self.env["pos.order"].new({})
        wizard = wizard_model.new({"name": "Cliente", "pricelist_id": denied.id})
        wizard.order_id = order
        with self.assertRaises(UserError):
            wizard.action_create_partner()

    def test_partner_create_from_pos_context(self):
        Pricelist = self.env["product.pricelist"]
        allowed = Pricelist.create(
            {"name": "PL permitida", "pos_quick_partner_selectable": True}
        )
        denied = Pricelist.create({"name": "PL no permitida"})
        Partner = self.env["res.partner"].with_context(pos_quick_partner_pricelist=True)
        with self.assertRaises(UserError):
            Partner.create({"name": "A", "property_product_pricelist": denied.id})
        partner = Partner.create(
            {"name": "B", "property_product_pricelist": allowed.id}
        )
        self.assertEqual(partner.property_product_pricelist, allowed)
