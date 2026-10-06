import base64
import io

import openpyxl

from odoo.tests.common import TransactionCase


class TestImportSalespeopleWizard(TransactionCase):

    def _import_salespeople(self, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['comercial', 'nombre'])
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        wizard = self.env['import.salespeople.wizard'].create({
            'file': base64.b64encode(buf.getvalue()),
            'file_name': 'comerciales.xlsx',
        })
        wizard.action_import_salespeople()
        return wizard

    def test_import_creates_then_updates_users_by_code(self):
        wizard = self._import_salespeople([[901, 'COMERCIAL UNO', ' '], [902, 'COMERCIAL DOS', None]])
        self.assertEqual((wizard.created_count, wizard.updated_count, wizard.error_count), (2, 0, 0))
        user = self.env['res.users'].search([('commercial_code', '=', '901')])
        self.assertEqual(user.name, 'COMERCIAL UNO')
        self.assertEqual(user.login, 'comercial_comercial_uno')

        wizard = self._import_salespeople([[901, 'COMERCIAL UNO RENOMBRADO', ' ']])
        self.assertEqual((wizard.created_count, wizard.updated_count), (0, 1))
        self.assertEqual(self.env['res.users'].search_count([('commercial_code', '=', '901')]), 1)
        self.assertEqual(user.name, 'COMERCIAL UNO RENOMBRADO')

    def test_contact_import_assigns_salesperson_and_payment_mode(self):
        self._import_salespeople([[903, 'COMERCIAL TRES', ' ']])
        contacts_wizard = self.env['import.contacts.wizard'].create({})
        results = {'created': [], 'updated': [], 'error': [], 'payment_term_unmatched': {}}
        row = [''] * 27
        row[0], row[1], row[6], row[10], row[26] = 7001, 'CLIENTE COM', '33333333P', 903, 'Metodo Nuevo'
        row_ok = list(row)
        row_ok[26] = 'TRANSFERENCIA ES57'
        row_note = list(row)
        row_note[0], row_note[1], row_note[6], row_note[10], row_note[26] = (
            7002, 'CLIENTE NOTA', '44444444A', 0, '03/03/26 DEUDA 465,94 VENTA A CUENTA')
        country = self.env.ref('base.es')
        salesperson_lookup = contacts_wizard._build_salesperson_lookup()
        mode_lookup = contacts_wizard._build_payment_mode_lookup()
        for r in (row_ok, row_note):
            contacts_wizard._process_import_row(
                r, country, results, salesperson_lookup=salesperson_lookup,
                payment_mode_lookup=mode_lookup)
        self.assertFalse(results['error'], results['error'])

        partner = self.env['res.partner'].search([('ref', '=', '7001')])
        self.assertEqual(partner.user_id.commercial_code, '903')
        self.assertEqual(partner.customer_payment_mode_id.name, 'TRANSFERENCIA ES57')
        note_partner = self.env['res.partner'].search([('ref', '=', '7002')])
        self.assertFalse(note_partner.customer_payment_mode_id)
        self.assertFalse(note_partner.user_id)
        self.assertEqual(len(results['payment_mode_unmatched']), 1)

        # Segunda vez: reutiliza el modo de pago, sin duplicarlo.
        count = self.env['account.payment.mode'].search_count([('name', '=', 'TRANSFERENCIA ES57')])
        contacts_wizard._process_import_row(
            row_ok, country, results, salesperson_lookup=salesperson_lookup,
            payment_mode_lookup=contacts_wizard._build_payment_mode_lookup())
        self.assertEqual(
            self.env['account.payment.mode'].search_count([('name', '=', 'TRANSFERENCIA ES57')]), count)

    def test_login_is_comercial_plus_slugified_name(self):
        wizard = self.env['import.salespeople.wizard']
        self.assertEqual(wizard._build_login('JULIAN MORA BRITO'), 'comercial_julian_mora_brito')
        self.assertEqual(wizard._build_login(' Jose Manuel Rodríguez '), 'comercial_jose_manuel_rodriguez')
