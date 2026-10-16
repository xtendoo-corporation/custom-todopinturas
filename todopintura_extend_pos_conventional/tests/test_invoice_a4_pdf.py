from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestInvoiceA4Pdf(HttpCase):
    def setUp(self):
        super().setUp()
        self.test_user = self.env["res.users"].create(
            {
                "name": "Usuario Factura A4",
                "login": "usuario_factura_a4",
                "password": "usuario_factura_a4_pwd",
                "group_ids": [(6, 0, [self.env.ref("account.group_account_invoice").id])],
            }
        )

    def test_invoice_a4_pdf_route(self):
        partner = self.env["res.partner"].create({"name": "Cliente Factura A4"})
        product = self.env["product.product"].create({"name": "Producto A4", "list_price": 10})
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_line_ids": [(0, 0, {"product_id": product.id, "quantity": 1, "price_unit": 10})],
            }
        )
        invoice.action_post()
        self.authenticate("usuario_factura_a4", "usuario_factura_a4_pwd")
        response = self.url_open(f"/todopintura_extend_pos_conventional/invoice_a4/{invoice.id}")
        self.assertEqual(response.status_code, 200, response.text[:300])
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        disposition = response.headers["Content-Disposition"]
        self.assertTrue(disposition.startswith("inline"), disposition)
        # Nombre legible y sin separadores de ruta (antes se guardaba como "_.pdf")
        expected = invoice.name.replace("/", "-")
        self.assertIn(f"Factura%20{expected}.pdf", disposition)

    def test_invoice_a4_pdf_route_not_found(self):
        self.authenticate("usuario_factura_a4", "usuario_factura_a4_pwd")
        response = self.url_open("/todopintura_extend_pos_conventional/invoice_a4/99999999")
        self.assertEqual(response.status_code, 404)
