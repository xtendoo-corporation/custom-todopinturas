import base64

from odoo.tests.common import TransactionCase


class TestImportContactsWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.wizard = self.env['import.contacts.wizard'].create({
            'file': base64.b64encode(b'dummy'),
            'file_name': 'dummy.xls',
        })

    def test_normalize_contact_vat_keeps_existing_prefix(self):
        vat, country_code = self.wizard._normalize_contact_vat('ESB94960701')

        self.assertEqual(vat, 'ESB94960701')
        self.assertEqual(country_code, 'ES')

    def test_find_existing_contact_returns_inactive_contact(self):
        contact = self.env['res.partner'].create({
            'name': 'CLIENTE PRUEBA',
            'ref': 1234,
            'vat': 'ESB94960701',
            'is_company': True,
            'active': False,
        })

        found_contact = self.wizard._find_existing_contact(1234, 'CLIENTE PRUEBA', 'ESB94960701')

        self.assertEqual(found_contact, contact)

    def test_create_or_update_contact_updates_existing_contact_by_vat(self):
        contact = self.env['res.partner'].create({
            'name': 'CLIENTE PRUEBA VAT',
            'vat': 'ESB94960701',
            'is_company': True,
            'street': 'ANTIGUA',
        })
        country = self.env['res.country'].search([('code', '=', 'ES')], limit=1)

        result = self.wizard._create_or_update_contact(1235, 'CLIENTE PRUEBA VAT', {
            'ref': 1235,
            'name': 'CLIENTE PRUEBA VAT',
            'street': 'NUEVA DIRECCION',
            'zip': '08021',
            'country_id': country.id,
            'phone': '934652558',
            'vat': 'ESB94960701',
            'email': 'cliente@example.com',
            'comment': 'Importado',
            'is_company': True,
        })

        contact.invalidate_recordset()
        contacts = self.env['res.partner'].search([
            ('parent_id', '=', False),
            ('is_company', '=', True),
            ('name', '=', 'CLIENTE PRUEBA VAT'),
        ])

        self.assertEqual(result, contact)
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contact.ref, '1235')
        self.assertEqual(contact.street, 'NUEVA DIRECCION')

    def test_find_existing_contact_by_iban(self):
        contact = self.env['res.partner'].create({
            'name': 'CLIENTE PRUEBA IBAN',
            'is_company': True,
        })
        self.env['res.partner.bank'].create({
            'acc_number': 'ES9121000418450200051332',
            'partner_id': contact.id,
        })

        found_contact = self.wizard._find_existing_contact('', 'CLIENTE PRUEBA IBAN', '', iban='ES91 2100 0418 4502 0005 1332')

        self.assertEqual(found_contact, contact)

    def test_parse_credit_limit_ignores_blank_strings(self):
        self.assertIsNone(self.wizard._parse_credit_limit('            '))
        self.assertIsNone(self.wizard._parse_credit_limit(''))
        self.assertEqual(self.wizard._parse_credit_limit('2223.75'), 2223.75)

