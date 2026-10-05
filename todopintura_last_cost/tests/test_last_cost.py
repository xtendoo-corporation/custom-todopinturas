from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestLastCost(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor test"})
        cls.categ_last = cls.env["product.category"].create(
            {"name": "Categoría último coste", "property_cost_method": "last"}
        )
        cls.categ_std = cls.env["product.category"].create(
            {"name": "Categoría estándar", "property_cost_method": "standard"}
        )
        cls.product_last = cls._create_product("Producto último", cls.categ_last)
        cls.product_std = cls._create_product("Producto estándar", cls.categ_std)

    @classmethod
    def _create_product(cls, name, categ):
        return cls.env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "categ_id": categ.id,
                "standard_price": 10.0,
            }
        )

    def _purchase(self, lines):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_qty": qty,
                            "price_unit": price, "discount": discount})
                    for product, qty, price, discount in lines
                ],
            }
        )
        order.button_confirm()
        return order

    def test_cost_method_is_standard_for_valuation(self):
        self.assertEqual(self.product_last.categ_id.property_cost_method, "last")
        self.assertEqual(self.product_last.cost_method, "standard")

    def test_confirm_updates_cost_net_of_discount(self):
        self._purchase([(self.product_last, 2, 50.0, 10.0)])
        self.assertAlmostEqual(self.product_last.standard_price, 45.0)

    def test_other_cost_method_is_not_touched(self):
        self._purchase([(self.product_std, 2, 50.0, 0.0)])
        self.assertAlmostEqual(self.product_std.standard_price, 10.0)

    def test_last_confirmed_order_wins(self):
        self._purchase([(self.product_last, 1, 30.0, 0.0)])
        self._purchase([(self.product_last, 1, 35.0, 0.0)])
        self.assertAlmostEqual(self.product_last.standard_price, 35.0)

    def test_zero_price_is_ignored(self):
        self._purchase([(self.product_last, 1, 0.0, 0.0)])
        self.assertAlmostEqual(self.product_last.standard_price, 10.0)

    def test_last_line_of_the_order_wins(self):
        self._purchase([(self.product_last, 1, 20.0, 0.0), (self.product_last, 1, 25.0, 0.0)])
        self.assertAlmostEqual(self.product_last.standard_price, 25.0)

    def test_uom_conversion(self):
        dozen = self.env.ref("uom.product_uom_dozen")
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [(0, 0, {
                    "product_id": self.product_last.id,
                    "product_qty": 1,
                    "product_uom_id": dozen.id,
                    "price_unit": 240.0,
                })],
            }
        )
        order.button_confirm()
        self.assertAlmostEqual(self.product_last.standard_price, 20.0)
