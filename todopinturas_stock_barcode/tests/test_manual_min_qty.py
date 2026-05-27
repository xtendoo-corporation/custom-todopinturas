# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase

class TestManualMinQty(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        cls.location = cls.warehouse.lot_stock_id
        cls.product = cls.env['product.product'].create({
            'name': 'Test Override Product',
            'default_code': 'OVERRIDE-TEST',
            'is_storable': True,
        })
        cls.orderpoint = cls.env['stock.warehouse.orderpoint'].create({
            'product_id': cls.product.id,
            'location_id': cls.location.id,
            'fixed_product_min_qty': 10.0,
            'fixed_product_max_qty': 20.0,
            'qty_multiple': 5,
        })

    def test_default_automated_recalculation(self):
        """By default, is_manual_min_qty is False and product_min_qty computes to fixed_product_min_qty."""
        self.assertFalse(self.orderpoint.is_manual_min_qty)
        self.assertEqual(self.orderpoint.product_min_qty, 10.0)
        self.assertEqual(self.orderpoint.product_max_qty, 10.0)

        # Updating fixed_product_min_qty should recompute product_min_qty
        self.orderpoint.fixed_product_min_qty = 15.0
        self.assertEqual(self.orderpoint.product_min_qty, 15.0)

    def test_manual_override_via_product_min_qty(self):
        """Setting product_min_qty manually should trigger inverse logic setting is_manual_min_qty to True and manual_min_qty to the value."""
        self.orderpoint.product_min_qty = 12.0
        
        # Checking that inverse fields are updated
        self.assertTrue(self.orderpoint.is_manual_min_qty)
        self.assertEqual(self.orderpoint.manual_min_qty, 12.0)

        # Checking that compute logic uses the manual_min_qty
        self.orderpoint.invalidate_recordset(['product_min_qty', 'product_max_qty'])
        self.assertEqual(self.orderpoint.product_min_qty, 12.0)
        self.assertEqual(self.orderpoint.product_max_qty, 12.0)

    def test_manual_override_via_manual_min_qty_field(self):
        """Setting manual_min_qty and is_manual_min_qty directly should also compute product_min_qty correctly."""
        self.orderpoint.write({
            'is_manual_min_qty': True,
            'manual_min_qty': 22.0,
        })
        self.assertEqual(self.orderpoint.product_min_qty, 22.0)
        self.assertEqual(self.orderpoint.product_max_qty, 22.0)

    def test_revert_to_automatic(self):
        """Setting is_manual_min_qty to False should revert product_min_qty to the automatic calculation."""
        self.orderpoint.product_min_qty = 30.0
        self.assertTrue(self.orderpoint.is_manual_min_qty)

        # Revert
        self.orderpoint.is_manual_min_qty = False
        self.assertEqual(self.orderpoint.product_min_qty, 10.0)
        self.assertEqual(self.orderpoint.product_max_qty, 10.0)

    def test_seasonal_dates_vs_manual_override(self):
        """Seasonal dates should be ignored if manual override is active, but respected when inactive."""
        # Create a seasonal date range for today
        self.env['stock.min.dates'].create({
            'orderpoint_id': self.orderpoint.id,
            'min_qty': 50.0,
            'max_qty': 50.0,
            'start_date': date(date.today().year, date.today().month, 1),
            'end_date': date(date.today().year + 1, 1, 1),
        })
        self.orderpoint.invalidate_recordset(['product_min_qty'])
        
        # When manual override is False, seasonal dates are respected
        self.assertEqual(self.orderpoint.product_min_qty, 50.0)

        # Enable manual override
        self.orderpoint.product_min_qty = 8.0
        self.assertTrue(self.orderpoint.is_manual_min_qty)
        self.assertEqual(self.orderpoint.product_min_qty, 8.0)

        # Revert back to automatic
        self.orderpoint.is_manual_min_qty = False
        self.assertEqual(self.orderpoint.product_min_qty, 50.0)
