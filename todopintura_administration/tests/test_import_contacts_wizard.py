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

    def test_find_existing_contact_does_not_steal_other_ref_by_iban(self):
        """Dos clientes distintos (p.ej. una cuenta de grupo) comparten IBAN.
        Si la fila trae un NUMERO CLIENTE que no existe todavía, no debe
        devolver el contacto del otro cliente (eso le roba la ficha y
        mezcla sus datos) -- debe comportarse como "no encontrado" para que
        se cree un contacto nuevo.
        """
        existing = self.env['res.partner'].create({
            'name': 'GRUPO LOGISTICO HISPALCARGO',
            'ref': '50468',
            'is_company': True,
        })
        self.env['res.partner.bank'].create({
            'acc_number': 'ES9121000418450200051332',
            'partner_id': existing.id,
        })

        found = self.wizard._find_existing_contact(
            '1807', 'HISPALCARGO LOGISTICA', '', iban='ES91 2100 0418 4502 0005 1332')

        self.assertFalse(found)

    def test_find_existing_contact_by_iban_still_claims_contact_without_ref(self):
        """Si el contacto encontrado por IBAN todavía no tiene ref propio
        (ficha antigua sin número de cliente), sí se puede reutilizar.
        """
        existing = self.env['res.partner'].create({
            'name': 'CLIENTE SIN REF',
            'is_company': True,
        })
        self.env['res.partner.bank'].create({
            'acc_number': 'ES9121000418450200051332',
            'partner_id': existing.id,
        })

        found = self.wizard._find_existing_contact(
            '1807', 'CLIENTE SIN REF', '', iban='ES91 2100 0418 4502 0005 1332')

        self.assertEqual(found, existing)

    def test_find_existing_contact_does_not_steal_other_ref_by_vat(self):
        existing = self.env['res.partner'].create({
            'name': 'EMPLEADOS',
            'ref': '9999999',
            'vat': 'ESB41089947',
            'is_company': True,
        })

        found = self.wizard._find_existing_contact('9003000', 'OTRO CLIENTE', 'ESB41089947')

        self.assertFalse(found)
        self.assertEqual(existing.ref, '9999999')

    def test_create_or_update_contact_creates_separate_contacts_sharing_iban(self):
        """Reproduce el bug real: dos números de cliente (1807 y 50468)
        comparten IBAN. Tras el fix, la reimportación debe crear/actualizar
        AMBOS contactos por separado, cada uno con sus propios datos.
        """
        iban = 'ES91 2100 0418 4502 0005 1332'
        country = self.env['res.country'].search([('code', '=', 'ES')], limit=1)

        record_50468 = {
            'ref': '50468', 'name': 'GRUPO LOGISTICO HISPALCARGO',
            'street': 'CALLE GRUPO', 'zip': '41001', 'country_id': country.id,
            'phone': '954000111', 'vat': '', 'email': 'grupo@example.com',
            'comment': '', 'is_company': True,
        }
        contact_50468, status_50468 = self.wizard._create_or_update_contact(
            '50468', 'GRUPO LOGISTICO HISPALCARGO', record_50468, iban=iban)
        self.wizard._ensure_bank_account(contact_50468, iban)
        self.assertEqual(status_50468, 'created')

        record_1807 = {
            'ref': '1807', 'name': 'HISPALCARGO LOGISTICA',
            'street': 'CALLE HISPALCARGO', 'zip': '41002', 'country_id': country.id,
            'phone': '954000222', 'vat': '', 'email': 'hispalcargo@example.com',
            'comment': '', 'is_company': True,
        }
        contact_1807, status_1807 = self.wizard._create_or_update_contact(
            '1807', 'HISPALCARGO LOGISTICA', record_1807, iban=iban)
        self.wizard._ensure_bank_account(contact_1807, iban)

        self.assertEqual(status_1807, 'created')
        self.assertNotEqual(contact_1807, contact_50468)
        self.assertEqual(contact_1807.ref, '1807')
        self.assertEqual(contact_1807.street, 'CALLE HISPALCARGO')
        self.assertEqual(contact_50468.ref, '50468')
        self.assertEqual(contact_50468.street, 'CALLE GRUPO')

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

    @staticmethod
    def _build_row(num_client, name, address='', cp='', telefono='', nif='',
                    forma_pago='', credit_limit='', iban='', email='',
                    condiciones_pago='', metodo_pago=''):
        """Construye una fila con el mismo layout posicional que
        _process_import_row espera (ver cell(idx) ahí), rellenando con
        cadenas vacías las columnas que no nos interesan para estos tests.
        """
        row = [''] * 27
        row[0] = num_client
        row[1] = name
        row[2] = address
        row[3] = cp
        row[4] = telefono
        row[6] = nif
        row[8] = forma_pago
        row[11] = credit_limit
        row[14] = iban
        row[23] = email
        row[25] = condiciones_pago
        row[26] = metodo_pago
        return row

    def _make_payment_term(self, name, condiciones, metodo=None):
        note = f'<p>Condiciones de pago: {condiciones}'
        if metodo:
            note += f'<br>Método de pago: {metodo}'
        note += '</p>'
        return self.env['account.payment.term'].create({'name': name, 'note': note})

    def test_payment_term_lookup_parses_condiciones_and_metodo_from_note(self):
        self._make_payment_term('CONTADO', 'CONTADO', 'CONTADO REPOSICION')
        self._make_payment_term('Pago inmediato', 'pago inmediato')

        lookup = self.wizard._build_payment_term_lookup()

        self.assertIn(('CONTADO', 'CONTADO REPOSICION'), lookup)
        self.assertIn(('PAGO INMEDIATO', ''), lookup)

    def test_process_import_row_prefers_condiciones_metodo_over_forma_pago_code(self):
        term_from_zaa = self._make_payment_term('CONTADO', 'CONTADO', 'CONTADO REPOSICION')
        term_from_code = self._make_payment_term('GIRO A 30 DIAS', '30 dias', 'GIRO')
        country = self.env['res.country'].search([('code', '=', 'ES')], limit=1)
        lookup = self.wizard._build_payment_term_lookup()
        results = {'created': [], 'updated': [], 'error': [], 'payment_term_unmatched': {}}

        row = self._build_row(
            7001, 'CLIENTE ZAA', nif='44444444A',
            forma_pago='1010',  # -> 'GIRO A 30 DIAS' si Z/AA no tuvieran prioridad
            condiciones_pago='CONTADO', metodo_pago='CONTADO REPOSICION',
        )
        self.wizard._process_import_row(row, country, results, payment_term_lookup=lookup)

        contact = self.env['res.partner'].search([('ref', '=', '7001')], limit=1)
        self.assertEqual(contact.property_payment_term_id, term_from_zaa)
        self.assertNotEqual(contact.property_payment_term_id, term_from_code)
        self.assertFalse(results['payment_term_unmatched'])

    def test_process_import_row_falls_back_to_forma_pago_when_no_zaa_match(self):
        term_from_code = self._make_payment_term('GIRO A 30 DIAS', '30 dias', 'GIRO')
        country = self.env['res.country'].search([('code', '=', 'ES')], limit=1)
        lookup = self.wizard._build_payment_term_lookup()
        results = {'created': [], 'updated': [], 'error': [], 'payment_term_unmatched': {}}

        row = self._build_row(
            7002, 'CLIENTE SIN ZAA', nif='55555555B',
            forma_pago='1010', condiciones_pago='', metodo_pago='',
        )
        self.wizard._process_import_row(row, country, results, payment_term_lookup=lookup)

        contact = self.env['res.partner'].search([('ref', '=', '7002')], limit=1)
        self.assertEqual(contact.property_payment_term_id, term_from_code)

    def test_process_import_row_records_unmatched_payment_term_combo(self):
        country = self.env['res.country'].search([('code', '=', 'ES')], limit=1)
        lookup = self.wizard._build_payment_term_lookup()
        results = {'created': [], 'updated': [], 'error': [], 'payment_term_unmatched': {}}

        row = self._build_row(
            7003, 'CLIENTE COMBO DESCONOCIDO', nif='66666666C',
            condiciones_pago='ALGO RARO', metodo_pago='OTRA COSA',
        )
        self.wizard._process_import_row(row, country, results, payment_term_lookup=lookup)

        contact = self.env['res.partner'].search([('ref', '=', '7003')], limit=1)
        self.assertFalse(contact.property_payment_term_id)
        self.assertEqual(results['payment_term_unmatched'].get(('ALGO RARO', 'OTRA COSA')), 1)

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

