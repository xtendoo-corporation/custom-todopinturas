from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestTodopinturaSalesReport(TransactionCase):
    def test_report_is_consistent(self):
        """La vista se crea y el margen es venta menos coste en cada línea."""
        lines = self.env["todopintura.sales.report"].search([], limit=200)
        for line in lines:
            self.assertAlmostEqual(line.margin, line.amount - line.cost, places=4)
        groups = self.env["todopintura.sales.report"]._read_group(
            [], ["doc_type"], ["amount:sum", "cost:sum", "margin:sum"]
        )
        for _doc_type, amount, cost, margin in groups:
            self.assertAlmostEqual(margin, amount - cost, places=4)

    def test_sale_order_confirmed_appears(self):
        partner = self.env["res.partner"].create({"name": "Cliente informe"})
        product = self.env["product.product"].create(
            {"name": "Producto informe", "standard_price": 6.0, "list_price": 10.0}
        )
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": 3})],
        })
        order.action_confirm()
        self.env.flush_all()
        line = self.env["todopintura.sales.report"].search(
            [("document_name", "=", order.name)]
        )
        self.assertEqual(len(line), 1)
        self.assertEqual(line.doc_type, "sale")
        self.assertEqual(line.delivery_status, "pending")
        self.assertAlmostEqual(line.amount, 30.0)
        self.assertAlmostEqual(line.cost, 18.0)
        self.assertAlmostEqual(line.margin, 12.0)
