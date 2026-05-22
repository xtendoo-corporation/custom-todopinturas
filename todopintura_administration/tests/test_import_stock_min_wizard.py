import base64
import io
from datetime import date

import openpyxl

from odoo.tests.common import TransactionCase


class TestImportStockMinWizard(TransactionCase):

    HEADER_ROW = [
        'PROV', 'NOMBRE', 'ALMACEN', 'NUMERO', 'DESCRIPCIO', 'UNIDAD PEDI', 'PORCENTAJEGENER', 'MINIMO',
        'ENERO', 'FEBRE', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOST', 'SEPBR', 'OCTUB', 'NOVBR',
        'DICBR', 'MAXIMO', 'OBSERVACIONES',
    ]

    def setUp(self):
        super().setUp()
        self.warehouse = self.env['stock.warehouse'].search([], limit=1)
        self.location = self.env['stock.location'].search([('complete_name', '=', 'WH/Central')], limit=1)
        if not self.location:
            self.location = self.env['stock.location'].create({
                'name': 'Central',
                'location_id': self.warehouse.view_location_id.id,
                'usage': 'internal',
            })
        self.product = self.env['product.product'].create({
            'name': 'Producto Stock Min Test',
            'default_code': 'STOCK-MIN-TEST',
            'is_storable': True,
        })
        self.wizard = self.env['import.stock.min.wizard'].create({
            'file': base64.b64encode(b'dummy'),
            'file_name': 'dummy.xlsx',
        })

    def _build_import_file(self, row_values):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(self.HEADER_ROW)
        sheet.append(row_values)
        buffer = io.BytesIO()
        workbook.save(buffer)
        return base64.b64encode(buffer.getvalue())

    def _month_row(self, min_qty=5, max_qty=10, qty_multiple=2, month_values=None):
        month_values = month_values or {}
        row = [''] * len(self.HEADER_ROW)
        row[2] = 1
        row[3] = self.product.default_code
        row[5] = qty_multiple
        row[7] = min_qty
        row[20] = max_qty
        for month in range(1, 13):
            row[7 + month] = month_values.get(month, '')
        return row

    def test_extract_layout_from_header_row_detects_12_months_and_maximo(self):
        header_row = [
            'PROV', 'NOMBRE', 'ALMACEN', 'NUMERO', 'DESCRIPCIO', 'UNIDAD PEDI', 'PORCENTAJEGENER', 'MINIMO',
            'ENERO', 'FEBRE', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOST', 'SEPBR', 'OCTUB', 'NOVBR',
            'DICBR', 'MAXIMO', 'OBSERVACIONES',
        ]

        layout = self.wizard._extract_layout_from_header_row(header_row)

        self.assertEqual(layout['location'], 2)
        self.assertEqual(layout['ref'], 3)
        self.assertEqual(layout['qty_multiple'], 5)
        self.assertEqual(layout['min_qty'], 7)
        self.assertEqual(layout['max_qty'], 20)
        self.assertEqual(layout['month_columns'][1], 8)
        self.assertEqual(layout['month_columns'][12], 19)
        self.assertEqual(len(layout['month_columns']), 12)

    def test_get_layout_falls_back_to_default_when_header_is_missing(self):
        row_index, layout = self.wizard._get_layout([
            ('dato', 'sin', 'cabecera'),
            ('otro', 'dato', 'sin', 'cabecera'),
        ])

        self.assertEqual(row_index, 1)
        self.assertEqual(layout, self.wizard._DEFAULT_LAYOUT)

    def test_normalize_header_removes_accents_and_symbols(self):
        self.assertEqual(self.wizard._normalize_header('Descripción % máx.'), 'DESCRIPCIONMAX')

    def test_import_stock_min_uses_fixed_min_when_all_month_columns_are_empty(self):
        wizard = self.env['import.stock.min.wizard'].create({
            'file': self._build_import_file(self._month_row(min_qty=6, max_qty=12, qty_multiple=3)),
            'file_name': 'stock_min.xlsx',
        })

        wizard.action_import_stock_min()

        orderpoint = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.location.id),
        ], limit=1)
        orderpoint.invalidate_recordset(['fixed_product_min_qty', 'fixed_product_max_qty', 'product_min_qty', 'product_max_qty', 'stock_min_dates_ids'])

        self.assertTrue(orderpoint)
        self.assertEqual(orderpoint.fixed_product_min_qty, 6)
        self.assertEqual(orderpoint.fixed_product_max_qty, 12)
        self.assertEqual(orderpoint.product_min_qty, 6)
        self.assertEqual(orderpoint.product_max_qty, 12)
        self.assertFalse(orderpoint.stock_min_dates_ids)

    def test_import_stock_min_creates_monthly_rows_and_uses_base_min_for_empty_months(self):
        current_month = date.today().month
        next_month = (current_month % 12) + 1
        year = date.today().year
        wizard = self.env['import.stock.min.wizard'].create({
            'file': self._build_import_file(
                self._month_row(
                    min_qty=4,
                    max_qty=10,
                    qty_multiple=2,
                    month_values={current_month: 9},
                )
            ),
            'file_name': 'stock_min.xlsx',
        })

        wizard.action_import_stock_min()

        orderpoint = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.location.id),
        ], limit=1)
        orderpoint.invalidate_recordset(['product_min_qty', 'stock_min_dates_ids'])
        period_records = orderpoint.stock_min_dates_ids.sorted('start_date')
        current_record = period_records.filtered(
            lambda record: record.start_date == date(year, current_month, 1)
        )
        next_record = period_records.filtered(
            lambda record: record.start_date <= date(year, next_month, 1) < record.end_date
        )

        expected_ranges = 1 if current_month in (1, 12) else 3
        self.assertEqual(len(period_records), expected_ranges)
        self.assertEqual(current_record.min_qty, 9)
        self.assertEqual(next_record.min_qty, 4)
        self.assertEqual(current_record.end_date, date(year, next_month, 1))
        self.assertEqual(orderpoint.product_min_qty, 9)

    def test_import_stock_min_merges_consecutive_months_with_the_same_quantity(self):
        wizard = self.env['import.stock.min.wizard'].create({
            'file': self._build_import_file(
                self._month_row(
                    min_qty=5,
                    max_qty=10,
                    month_values={1: 8, 2: 8, 3: 8, 4: 8, 5: 8, 6: 8},
                )
            ),
            'file_name': 'stock_min.xlsx',
        })

        wizard.action_import_stock_min()

        orderpoint = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.location.id),
        ], limit=1)
        year = date.today().year
        orderpoint.invalidate_recordset(['stock_min_dates_ids'])
        period_records = orderpoint.stock_min_dates_ids.sorted('start_date')

        self.assertEqual(len(period_records), 2)
        self.assertEqual(period_records[0].min_qty, 8)
        self.assertEqual(period_records[0].start_date, date(year, 1, 1))
        self.assertEqual(period_records[0].end_date, date(year, 7, 1))
        self.assertEqual(period_records[1].min_qty, 5)
        self.assertEqual(period_records[1].start_date, date(year, 7, 1))
        self.assertEqual(period_records[1].end_date, date(year + 1, 1, 1))
        self.assertEqual(period_records.mapped('product_id'), self.product)

    def test_import_stock_min_removes_monthly_rows_when_product_becomes_fixed(self):
        seasonal_wizard = self.env['import.stock.min.wizard'].create({
            'file': self._build_import_file(self._month_row(min_qty=5, max_qty=10, month_values={1: 8})),
            'file_name': 'stock_min.xlsx',
        })
        seasonal_wizard.action_import_stock_min()

        fixed_wizard = self.env['import.stock.min.wizard'].create({
            'file': self._build_import_file(self._month_row(min_qty=7, max_qty=14, qty_multiple=1)),
            'file_name': 'stock_min.xlsx',
        })
        fixed_wizard.action_import_stock_min()

        orderpoint = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.location.id),
        ], limit=1)
        orderpoint.invalidate_recordset(['fixed_product_min_qty', 'fixed_product_max_qty', 'product_min_qty', 'product_max_qty', 'stock_min_dates_ids'])

        self.assertFalse(orderpoint.stock_min_dates_ids)
        self.assertEqual(orderpoint.fixed_product_min_qty, 7)
        self.assertEqual(orderpoint.fixed_product_max_qty, 14)
        self.assertEqual(orderpoint.product_min_qty, 7)
        self.assertEqual(orderpoint.product_max_qty, 14)

