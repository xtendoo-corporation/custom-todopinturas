from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductPricelistMetrics(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_tmpl = cls.env["product.template"].create(
            {
                "name": "Producto tarifa métricas",
                "type": "consu",
                "list_price": 100.0,
                "standard_price": 20.0,
            }
        )
        cls.product = cls.product_tmpl.product_variant_id
        cls.pricelist = cls.env["product.pricelist"].create({
            "name": "Tarifa métricas",
            "currency_id": cls.env.company.currency_id.id,
        })

    def test_fixed_rule_displays_total_and_margin(self):
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "product_tmpl_id": self.product_tmpl.id,
                "applied_on": "1_product",
                "compute_price": "fixed",
                "fixed_price": 50.0,
                "min_quantity": 2.0,
            }
        )

        self.assertEqual(rule.display_final_price, 50.0)
        self.assertEqual(rule.display_total_price, 100.0)
        self.assertEqual(rule.display_cost_price, 20.0)
        self.assertEqual(rule.display_margin_amount, 30.0)
        self.assertEqual(rule.display_margin_percent, 60.0)

    def test_percentage_rule_displays_total_and_margin(self):
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "product_tmpl_id": self.product_tmpl.id,
                "applied_on": "1_product",
                "compute_price": "percentage",
                "percent_price": 10.0,
                "min_quantity": 3.0,
            }
        )

        self.assertEqual(rule.display_final_price, 90.0)
        self.assertEqual(rule.display_total_price, 270.0)
        self.assertEqual(rule.display_cost_price, 20.0)
        self.assertEqual(rule.display_margin_amount, 70.0)
        self.assertAlmostEqual(rule.display_margin_percent, 77.7777777778, places=2)

    def test_formula_rule_based_on_cost_displays_margin(self):
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "product_tmpl_id": self.product_tmpl.id,
                "applied_on": "1_product",
                "compute_price": "formula",
                "base": "standard_price",
                "price_markup": 25.0,
                "price_surcharge": 5.0,
            }
        )

        self.assertEqual(rule.display_final_price, 30.0)
        self.assertEqual(rule.display_total_price, 30.0)
        self.assertEqual(rule.display_cost_price, 20.0)
        self.assertEqual(rule.display_margin_amount, 10.0)
        self.assertAlmostEqual(rule.display_margin_percent, 33.3333333333, places=2)


