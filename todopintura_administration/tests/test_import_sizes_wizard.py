import base64
import io

import openpyxl

from odoo.tests.common import TransactionCase


class TestImportSizesWizard(TransactionCase):

    def _import_sizes(self, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['NUMERO', 'TAMAÑO'])
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        wizard = self.env['import.sizes.wizard'].create({
            'file': base64.b64encode(buf.getvalue()),
            'file_name': 'tamanos.xlsx',
        })
        wizard.action_import_sizes()
        return wizard

    def test_import_creates_updates_and_skips_code_zero(self):
        wizard = self._import_sizes([[0, '      --'], [9001, ' 5 Kg/Lt'], [9002, '  1000lt']])
        self.assertEqual((wizard.created_count, wizard.updated_count, wizard.error_count), (2, 0, 0))
        self.assertFalse(self.env['product.size'].search([('code', '=', 0)]))
        self.assertEqual(self.env['product.size'].search([('code', '=', 9002)]).name, '1000lt')

        wizard = self._import_sizes([[9001, '5 Kg']])
        self.assertEqual((wizard.created_count, wizard.updated_count), (0, 1))
        self.assertEqual(self.env['product.size'].search_count([('code', '=', 9001)]), 1)

    def test_product_record_gets_size_from_values(self):
        size = self.env['product.size'].create({'code': 3, 'name': '3 Kg/Lt'})
        products_wizard = self.env['import.products.wizard'].create({})
        row = [''] * 49
        row[0], row[1], row[29] = 987003, 'PRODUCTO TAMAÑO', 0
        values = products_wizard._prepare_product_values(row)
        self.assertEqual(values['size_code'], 3)
        values['size'] = size
        record, _pos, _categ = products_wizard._build_product_record(values)
        self.assertEqual(record['size_id'], size.id)
        self.assertEqual(record['weight'], 3)
        self.assertAlmostEqual(record['volume'], 0.003)
        product = products_wizard._create_or_update_product(record)
        self.assertEqual(product.size_id, size)

    def test_parse_weight_volume_from_size_name(self):
        parse = self.env['product.size']._parse_weight_volume
        cases = {
            '5 Kg/Lt': (5, 0.005),
            '1,250k/L': (1.25, 0.00125),
            '8,5LT/KG': (8.5, 0.0085),
            '750Gr/Ml': (0.75, 0.00075),
            '22 kg': (22, 0),
            '1.200KG': (1200, 0),
            '200 LT.': (0, 0.2),
            '1000lt': (0, 1),
            '290ML': (0, 0.00029),
            '2,24 Ml': (0, 0),
            '26,50MT2': (0, 0),
            'Rollo': (0, 0),
            '--': (0, 0),
        }
        for name, (weight, volume) in cases.items():
            result = parse(name)
            self.assertAlmostEqual(result[0], weight, msg=name)
            self.assertAlmostEqual(result[1], volume, msg=name)
