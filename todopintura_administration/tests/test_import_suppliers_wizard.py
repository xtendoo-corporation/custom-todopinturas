import base64

from odoo.tests.common import TransactionCase


class TestImportSuppliersWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.wizard = self.env['import.suppliers.wizard'].create({
            'file': base64.b64encode(b'dummy'),
            'file_name': 'dummy.xls',
        })

    def test_normalize_supplier_vat_keeps_existing_prefix(self):
        vat, country_code = self.wizard._normalize_supplier_vat('ESB94960701')

        self.assertEqual(vat, 'ESB94960701')
        self.assertEqual(country_code, 'ES')

    def test_find_existing_supplier_returns_inactive_supplier(self):
        supplier = self.env['res.partner'].create({
            'name': 'SAN MARCO-COLORES,S.L.U.',
            'ref': '01234',
            'vat': 'ESB94960701',
            'is_company': True,
            'active': False,
        })

        found_supplier = self.wizard._find_existing_supplier('01234', 'SAN MARCO-COLORES,S.L.U.', 'ESB94960701')

        self.assertEqual(found_supplier, supplier)

    def test_create_or_update_supplier_updates_existing_supplier_by_vat(self):
        supplier = self.env['res.partner'].create({
            'name': 'SAN MARCO-COLORES,S.L.U.',
            'vat': 'ESB94960701',
            'is_company': True,
            'street': 'ANTIGUA',
        })
        country = self.env['res.country'].search([('code', '=', 'ES')], limit=1)

        result = self.wizard._create_or_update_supplier('01234', 'SAN MARCO-COLORES,S.L.U.', {
            'ref': '01234',
            'name': 'SAN MARCO-COLORES,S.L.U.',
            'street': 'NUEVA DIRECCION',
            'zip': '08021',
            'is_company': True,
            'country_id': country.id,
            'phone': '934652558',
            'vat': 'ESB94960701',
            'active': True,
            'comment': 'Importado',
        })

        supplier.invalidate_recordset()
        suppliers = self.env['res.partner'].search([
            ('parent_id', '=', False),
            ('is_company', '=', True),
            ('name', '=', 'SAN MARCO-COLORES,S.L.U.'),
        ])

        self.assertEqual(result, supplier)
        self.assertEqual(len(suppliers), 1)
        self.assertEqual(supplier.ref, '01234')
        self.assertEqual(supplier.street, 'NUEVA DIRECCION')

