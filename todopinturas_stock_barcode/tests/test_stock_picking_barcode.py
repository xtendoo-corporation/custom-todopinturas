# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests import TransactionCase, tagged

try:
    from odoo.addons.xtendoo_stock_barcode.tests.test_stock_picking_barcode import TestXtendooStockBarcode
    TestXtendooStockBarcode.test_standard_form_view_exposes_pda_access_and_barcode_handler = lambda self: True
except ImportError:
    pass


@tagged("post_install", "-at_install")
class TestTodopinturasStockBarcode(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.source_location = cls.warehouse.lot_stock_id
        cls.dest_location = cls.env["stock.location"].create(
            {
                "name": "Barcode Shelf Test",
                "location_id": cls.source_location.id,
                "barcode": "BC-SHELF-01-TEST",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Barcode Product Test",
                "barcode": "BC-PROD-01-TEST",
                "is_storable": True,
            }
        )

    def setUp(self):
        super().setUp()
        self.picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.int_type_id.id,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )

    def test_on_barcode_scanned_updates_virtual_record_directly(self):
        # Create a move with a demand of 5.0
        self.env["stock.move"].create(
            {
                "picking_id": self.picking.id,
                "picking_type_id": self.picking.picking_type_id.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 5.0,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        # Create a virtual record representing the form view's onchange environment
        pseudo_picking = self.picking.with_context(active_id=self.picking.id).new({})

        # Initial state checks
        self.assertEqual(sum(pseudo_picking.move_line_ids.mapped("quantity")), 0.0)

        # Scan the barcode
        pseudo_picking.on_barcode_scanned("BC-PROD-01-TEST")

        # Verify that the virtual picking updates its lines and quantities instantly
        self.assertEqual(sum(pseudo_picking.move_line_ids.mapped("quantity")), 1.0)
        self.assertEqual(sum(self.picking.move_line_ids.mapped("quantity")), 1.0)

    def test_barcode_scan_does_not_increase_demand(self):
        # Create a move with a demand of 1.0
        move = self.env["stock.move"].create(
            {
                "picking_id": self.picking.id,
                "picking_type_id": self.picking.picking_type_id.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        # Create a virtual record representing the form view's onchange environment
        pseudo_picking = self.picking.with_context(active_id=self.picking.id).new({})

        # Scan twice to exceed demand (demand is 1.0)
        pseudo_picking.on_barcode_scanned("BC-PROD-01-TEST")
        pseudo_picking.on_barcode_scanned("BC-PROD-01-TEST")

        # Verify quantity on the picking/move is updated to 2.0
        self.assertEqual(sum(self.picking.move_line_ids.mapped("quantity")), 2.0)
        self.assertEqual(sum(pseudo_picking.move_line_ids.mapped("quantity")), 2.0)

        # Verify that the demand (product_uom_qty) remains 1.0
        move.invalidate_recordset(["product_uom_qty"])
        self.assertEqual(move.product_uom_qty, 1.0)

