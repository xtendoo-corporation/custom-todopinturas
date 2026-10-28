from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleWorkflow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_ok = cls.env["res.partner"].create(
            {"name": "Con crédito", "pos_credit_sale_enabled": True}
        )
        cls.partner_ko = cls.env["res.partner"].create({"name": "Sin crédito"})
        cls.pricelist = cls.env["product.pricelist"].create({"name": "PL otra"})

    def test_sale_to_partner_without_credit_blocked(self):
        with self.assertRaises(ValidationError):
            self.env["sale.order"].create({"partner_id": self.partner_ko.id})
        order = self.env["sale.order"].create({"partner_id": self.partner_ok.id})
        with self.assertRaises(ValidationError):
            order.write({"partner_id": self.partner_ko.id})

    def test_child_contact_uses_commercial_partner(self):
        child = self.env["res.partner"].create(
            {"name": "Contacto", "parent_id": self.partner_ok.id, "type": "contact"}
        )
        self.assertTrue(
            self.env["sale.order"].create({"partner_id": child.id})
        )

    def test_pricelist_and_validity_locked(self):
        user = self.env["res.users"].create(
            {
                "name": "Vendedor test",
                "login": "vendedor_test_workflow",
                "group_ids": [
                    (6, 0, [self.env.ref("sales_team.group_sale_manager").id])
                ],
            }
        )
        order = (
            self.env["sale.order"]
            .create({"partner_id": self.partner_ok.id})
            .with_user(user)
        )
        with self.assertRaises(UserError):
            order.write({"pricelist_id": self.pricelist.id})
        with self.assertRaises(UserError):
            order.write({"validity_date": "2030-01-01"})
        # Reescribir el mismo valor no es un cambio
        order.write({"pricelist_id": order.pricelist_id.id})

    def test_partner_change_recomputes_pricelist(self):
        order = self.env["sale.order"].create({"partner_id": self.partner_ok.id})
        other = self.env["res.partner"].create(
            {
                "name": "Otro con crédito",
                "pos_credit_sale_enabled": True,
                "property_product_pricelist": self.pricelist.id,
            }
        )
        order.write({"partner_id": other.id})
        self.assertEqual(order.pricelist_id, self.pricelist)
