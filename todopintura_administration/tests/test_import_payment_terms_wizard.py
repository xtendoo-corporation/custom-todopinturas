import base64
import io

import openpyxl

from odoo.tests.common import TransactionCase


class TestImportPaymentTermsWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.wizard = self.env['import.payment.terms.wizard'].create({
            'file': base64.b64encode(b'dummy'),
            'file_name': 'dummy.xls',
        })

    @staticmethod
    def _build_xlsx(rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['codigode pago', 'descri', 'Condiciones de pago', 'metodo de pago'])
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def test_prepare_payment_term_record_builds_note(self):
        record = self.wizard._prepare_payment_term_record(3017, 'REPOSICION TALON 30 DIAS', '30 DIAS F.F.', 'CHEQUE')

        self.assertEqual(record['referencia_todopintura'], 3017)
        self.assertEqual(record['name'], 'REPOSICION TALON 30 DIAS')
        self.assertIn('30 DIAS F.F.', record['note'])
        self.assertIn('CHEQUE', record['note'])

    def test_create_or_update_payment_term_creates_new(self):
        record = self.wizard._prepare_payment_term_record(9999, 'FORMA NUEVA', 'CONTADO', 'CONTADO REPOSICION')

        payment_term, status = self.wizard._create_or_update_payment_term(9999, record)

        self.assertEqual(status, 'created')
        self.assertEqual(payment_term.referencia_todopintura, 9999)
        self.assertEqual(payment_term.name, 'FORMA NUEVA')

    def test_create_or_update_payment_term_updates_existing_without_duplicating(self):
        existing = self.env['account.payment.term'].create({
            'referencia_todopintura': 1010,
            'name': 'NOMBRE ANTIGUO',
        })

        record = self.wizard._prepare_payment_term_record(1010, 'NOMBRE NUEVO', '30 DIAS F.F.', 'GIRO')
        payment_term, status = self.wizard._create_or_update_payment_term(1010, record)

        self.assertEqual(status, 'updated')
        self.assertEqual(payment_term, existing)
        self.assertEqual(payment_term.name, 'NOMBRE NUEVO')

        terms = self.env['account.payment.term'].search([('referencia_todopintura', '=', 1010)])
        self.assertEqual(len(terms), 1)

    def test_action_import_payment_terms_creates_then_updates_without_duplicating(self):
        xlsx_data = self._build_xlsx([
            [3017, 'REPOSICION TALON 30 DIAS', '30 DIAS F.F.', 'CHEQUE'],
            [1010, '30 DIAS', '30 DIAS F.F.', 'GIRO'],
        ])

        first_wizard = self.env['import.payment.terms.wizard'].create({
            'file': base64.b64encode(xlsx_data),
            'file_name': 'formas_de_pago.xlsx',
        })
        first_wizard.action_import_payment_terms()

        self.assertEqual(first_wizard.state, 'done')
        self.assertEqual(first_wizard.created_count, 2)
        self.assertEqual(first_wizard.updated_count, 0)
        self.assertEqual(first_wizard.error_count, 0)
        self.assertIn('REPOSICION TALON 30 DIAS', first_wizard.log)

        second_wizard = self.env['import.payment.terms.wizard'].create({
            'file': base64.b64encode(xlsx_data),
            'file_name': 'formas_de_pago.xlsx',
        })
        second_wizard.action_import_payment_terms()

        self.assertEqual(second_wizard.created_count, 0)
        self.assertEqual(second_wizard.updated_count, 2)

        terms = self.env['account.payment.term'].search([
            ('referencia_todopintura', 'in', [3017, 1010]),
        ])
        self.assertEqual(len(terms), 2)

    def test_action_reset_clears_state_and_file(self):
        xlsx_data = self._build_xlsx([[3000, 'CONTADO', 'CONTADO', 'CONTADO REPOSICION']])
        wizard = self.env['import.payment.terms.wizard'].create({
            'file': base64.b64encode(xlsx_data),
            'file_name': 'formas_de_pago.xlsx',
        })
        wizard.action_import_payment_terms()
        self.assertEqual(wizard.state, 'done')

        wizard.action_reset()

        self.assertEqual(wizard.state, 'upload')
        self.assertFalse(wizard.file)
        self.assertFalse(wizard.log)
