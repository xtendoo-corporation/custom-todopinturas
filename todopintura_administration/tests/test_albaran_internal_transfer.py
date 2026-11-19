# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase, tagged

REPORT = "todopintura_administration.report_albaran_todopintura_document"


@tagged("post_install", "-at_install")
class TestAlbaranInternalTransfer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env["stock.warehouse"]
        cls.origin = Warehouse.create({"name": "Tienda Origen Albaran", "code": "TOA"})
        cls.dest = Warehouse.create({"name": "Tienda Destino Albaran", "code": "TDA"})
        cls.product = cls.env["product.product"].create(
            {"name": "Producto Albaran Traspaso", "default_code": "ALB-TR-01", "is_storable": True}
        )

    def _picking(self, picking_type, source, destination):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "move_ids": [
                    (0, 0, {
                        "product_id": self.product.id,
                        "product_uom_qty": 3,
                        "location_id": source.id,
                        "location_dest_id": destination.id,
                    })
                ],
            }
        )

    def _html(self, picking):
        html = self.env["ir.actions.report"]._render_qweb_html(REPORT, picking.ids)[0]
        return html.decode() if isinstance(html, bytes) else html

    def test_internal_transfer_prints_number_warehouses_and_lines(self):
        picking = self._picking(
            self.origin.int_type_id, self.origin.lot_stock_id, self.dest.lot_stock_id
        )
        self.assertTrue(picking._tp_is_internal_transfer())
        self.assertEqual(picking._tp_report_copies(), [False])
        html = self._html(picking)
        self.assertIn(picking.name, html)
        self.assertIn("Tienda Origen Albaran", html)
        self.assertIn("Tienda Destino Albaran", html)
        self.assertIn("ALB-TR-01", html)
        self.assertIn("Producto Albaran Traspaso", html)
        # Simplified: no customer copies, no size/price columns.
        self.assertNotIn("COPIA PARA EL CLIENTE", html)
        self.assertNotIn("TAMAÑO", html)

    def test_delivery_keeps_the_customer_layout(self):
        picking = self._picking(
            self.origin.out_type_id,
            self.origin.lot_stock_id,
            self.env.ref("stock.stock_location_customers"),
        )
        self.assertFalse(picking._tp_is_internal_transfer())
        self.assertEqual(
            picking._tp_report_copies(), ["COPIA INTERNA", "COPIA PARA EL CLIENTE"]
        )
        html = self._html(picking)
        self.assertIn("COPIA PARA EL CLIENTE", html)
        self.assertIn("TAMAÑO", html)
        self.assertNotIn("ALMACÉN ORIGEN", html)

    def test_deposit_transfer_keeps_the_customer_layout(self):
        deposit = self.env["stock.location"].create({"name": "Depósito", "usage": "transit"})
        picking = self._picking(
            self.origin.int_type_id, self.origin.lot_stock_id, deposit
        )
        self.assertFalse(picking._tp_is_internal_transfer())

    def test_receipt_of_a_transfer_between_warehouses_is_simplified(self):
        """Recepción en la tienda destino (tipo «Recepciones», origen y destino internos)."""
        picking = self._picking(
            self.dest.in_type_id, self.origin.lot_stock_id, self.dest.lot_stock_id
        )
        self.assertEqual(picking.picking_type_code, "incoming")
        self.assertTrue(picking._tp_is_internal_transfer())
        html = self._html(picking)
        self.assertIn("Tienda Origen Albaran", html)
        self.assertIn("Tienda Destino Albaran", html)
        self.assertNotIn("COPIA PARA EL CLIENTE", html)
        self.assertNotIn("TAMAÑO", html)

    def test_supplier_receipt_keeps_the_customer_layout(self):
        picking = self._picking(
            self.dest.in_type_id,
            self.env.ref("stock.stock_location_suppliers"),
            self.dest.lot_stock_id,
        )
        self.assertFalse(picking._tp_is_internal_transfer())
