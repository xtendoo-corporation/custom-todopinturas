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

    def test_albaran_pdf_route(self):
        picking_type = self.env["stock.picking.type"].search([("code", "=", "outgoing")], limit=1)
        product = self.env["product.product"].create({"name": "Producto Albaran", "list_price": 10})
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "partner_id": self.env["res.partner"].create({"name": "Cliente Albaran"}).id,
                "move_ids": [
                    (0, 0, {
                        "product_id": product.id,
                        "product_uom_qty": 1,
                        "location_id": picking_type.default_location_src_id.id,
                        "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                    })
                ],
            }
        )
        self.test_user.write({"group_ids": [(4, self.env.ref("stock.group_stock_user").id)]})
        self.authenticate("usuario_factura_a4", "usuario_factura_a4_pwd")
        response = self.url_open(f"/todopintura_extend_pos_conventional/albaran_pdf/{picking.id}")
        self.assertEqual(response.status_code, 200, response.text[:300])
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertTrue(response.headers["Content-Disposition"].startswith("inline"))

    def _make_picking(self, partner):
        picking_type = self.env["stock.picking.type"].search([("code", "=", "outgoing")], limit=1)
        product = self.env["product.product"].create({"name": "Producto Valorado", "list_price": 10})
        customers = self.env.ref("stock.stock_location_customers")
        return self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": customers.id,
                "partner_id": partner.id,
                "move_ids": [
                    (0, 0, {
                        "product_id": product.id,
                        "product_uom_qty": 1,
                        "location_id": picking_type.default_location_src_id.id,
                        "location_dest_id": customers.id,
                    })
                ],
            }
        )

    def test_albaran_report_depends_on_partner_valued_flag(self):
        standard = self.env["res.partner"].create({"name": "Cliente Estandar"})
        valued = self.env["res.partner"].create(
            {"name": "Cliente Valorado", "delivery_report_print_type": "valued"}
        )
        normal_report = self.env.ref("todopintura_administration.action_report_albaran_todopintura")
        valued_report = self.env.ref("todopintura_administration.action_report_albaran_todopintura_valorado")
        self.assertEqual(self._make_picking(standard)._tp_albaran_report(), normal_report)
        self.assertEqual(self._make_picking(valued)._tp_albaran_report(), valued_report)
        self.assertEqual(self._make_picking(standard)._tp_albaran_report(valued=True), valued_report)

    def test_albaran_pdf_route_uses_valued_report_for_valued_partner(self):
        valued = self.env["res.partner"].create(
            {"name": "Cliente Valorado HTTP", "delivery_report_print_type": "valued"}
        )
        picking = self._make_picking(valued)
        self.test_user.write({"group_ids": [(4, self.env.ref("stock.group_stock_user").id)]})
        self.authenticate("usuario_factura_a4", "usuario_factura_a4_pwd")
        response = self.url_open(f"/todopintura_extend_pos_conventional/albaran_pdf/{picking.id}")
        self.assertEqual(response.status_code, 200, response.text[:300])
