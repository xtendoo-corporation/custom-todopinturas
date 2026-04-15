import base64

from odoo.tests.common import TransactionCase


class TestImportClientTariffsWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.wizard = self.env['import.client.tariffs.wizard'].create({
            'file': base64.b64encode(b'dummy'),
            'file_name': 'dummy.xlsx',
        })

    def test_safe_int_returns_none_for_invalid_text(self):
        value = self.wizard._safe_int('LINEA   ', 'price_line', 7, default=0)

        self.assertIsNone(value)

    def test_safe_int_accepts_numeric_strings(self):
        value = self.wizard._safe_int(' 12 ', 'price_line', 7, default=0)

        self.assertEqual(value, 12)

    def test_cell_to_text_strips_whitespace(self):
        self.assertEqual(self.wizard._cell_to_text('  ABC  '), 'ABC')
        self.assertEqual(self.wizard._cell_to_text(None, default='0'), '0')

    def test_upsert_pricelist_item_registers_row_when_base_pricelist_is_missing(self):
        errors = []

        result = self.wizard._upsert_pricelist_item(
            errors,
            12,
            {
                'pricelist_id': self.env['product.pricelist'].create({'name': 'Tarifa Test'}).id,
                'applied_on': '3_global',
                'compute_price': 'formula',
                'base': 'pricelist',
            },
            client_ref='1000',
            product_code='P001',
        )

        self.assertFalse(result)
        self.assertEqual(len(errors), 1)
        self.assertIn('Fila 12:', errors[0])
        self.assertIn('base', errors[0])

    def test_ensure_base_pricelist_creates_missing_tariff(self):
        pricelist = self.wizard._ensure_base_pricelist(3)

        self.assertTrue(pricelist)
        self.assertEqual(pricelist.name, 'Tarifa 3')

