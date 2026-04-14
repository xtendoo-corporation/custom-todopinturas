import base64

from odoo.tests.common import TransactionCase


class TestImportStockMinWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.wizard = self.env['import.stock.min.wizard'].create({
            'file': base64.b64encode(b'dummy'),
            'file_name': 'dummy.xlsx',
        })

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

