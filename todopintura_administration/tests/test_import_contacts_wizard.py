import base64
import io

import openpyxl

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

        result, status = self.wizard._create_or_update_contact(1235, 'CLIENTE PRUEBA VAT', {
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
        self.assertEqual(status, 'updated')
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contact.ref, '1235')
        self.assertEqual(contact.street, 'NUEVA DIRECCION')

    def test_create_or_update_contact_creates_new_contact(self):
        country = self.env['res.country'].search([('code', '=', 'ES')], limit=1)

        result, status = self.wizard._create_or_update_contact(9999, 'CLIENTE NUEVO', {
            'ref': 9999,
            'name': 'CLIENTE NUEVO',
            'street': 'CALLE NUEVA',
            'zip': '08021',
            'country_id': country.id,
            'phone': '934652558',
            'vat': '',
            'email': 'nuevo@example.com',
            'comment': '',
            'is_company': True,
        })

        self.assertEqual(status, 'created')
        self.assertEqual(result.name, 'CLIENTE NUEVO')

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

    @staticmethod
    def _build_xlsx(rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['NUMERO CLIENTE', 'NOMBRE DE CLIENTE', 'DIRECCION', 'CODIGO POSTAL',
                   'TELEFONO 1', 'TELEFONO 2', 'DNI O CFIF'])
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def test_action_import_contacts_creates_then_updates_without_duplicating(self):
        xlsx_data = self._build_xlsx([
            [5001, 'CLIENTE UNO', 'CALLE UNO', 41001, 954000001, 0, '11111111H'],
            [5002, 'CLIENTE DOS', 'CALLE DOS', 41002, 954000002, 0, '22222222J'],
        ])

        first_wizard = self.env['import.contacts.wizard'].create({
            'file': base64.b64encode(xlsx_data),
            'file_name': 'clientes.xlsx',
        })
        first_wizard.action_import_contacts()

        self.assertEqual(first_wizard.state, 'done')
        self.assertEqual(first_wizard.created_count, 2)
        self.assertEqual(first_wizard.updated_count, 0)
        self.assertEqual(first_wizard.error_count, 0)
        self.assertIn('CLIENTE UNO', first_wizard.log)

        second_wizard = self.env['import.contacts.wizard'].create({
            'file': base64.b64encode(xlsx_data),
            'file_name': 'clientes.xlsx',
        })
        second_wizard.action_import_contacts()

        self.assertEqual(second_wizard.created_count, 0)
        self.assertEqual(second_wizard.updated_count, 2)

        contacts = self.env['res.partner'].search([
            ('ref', 'in', ['5001', '5002']),
            ('is_company', '=', True),
        ])
        self.assertEqual(len(contacts), 2)

    def test_action_reset_clears_state_and_file(self):
        xlsx_data = self._build_xlsx([[6001, 'CLIENTE RESET', 'CALLE RESET', 41003, 954000003, 0, '33333333K']])
        wizard = self.env['import.contacts.wizard'].create({
            'file': base64.b64encode(xlsx_data),
            'file_name': 'clientes.xlsx',
        })
        wizard.action_import_contacts()
        self.assertEqual(wizard.state, 'done')

        wizard.action_reset()

        self.assertEqual(wizard.state, 'upload')
        self.assertFalse(wizard.file)
        self.assertFalse(wizard.log)

