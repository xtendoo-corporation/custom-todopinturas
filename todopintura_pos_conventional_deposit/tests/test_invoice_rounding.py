from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestInvoiceRounding(PosConventionalTestCommon):

    def _make_invoice(self, order_total):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        order.amount_total = order_total
        vals = order._prepare_invoice_vals()
        vals["invoice_line_ids"] = [(0, 0, {
            "name": "Línea",
            "quantity": 1,
            "price_unit": 7.2164,
            "tax_ids": [(6, 0, self.product.taxes_id.ids)],
        })]
        invoice = order._create_invoice(vals)
        return order, invoice

    def test_invoice_total_matches_pos_order_total(self):
        tax = self.env["account.tax"].create({
            "name": "IVA 21 test", "amount": 21.0, "amount_type": "percent", "type_tax_use": "sale",
        })
        self.product.taxes_id = tax
        order, invoice = self._make_invoice(8.73)
        self.assertEqual(invoice.amount_total, 8.73)
        self.assertEqual(invoice.amount_residual, 8.73)
