from odoo.tests.common import TransactionCase


class TestTodopinturaExcelParser(TransactionCase):
    """Pruebas para el parseador de Excel."""

    def test_parser_initialization(self):
        """Verifica que el parser se inicializa correctamente."""
        from todopintura_importer.utils.excel_parser import TodopinturaExcelParser

        # Mock data
        parser = TodopinturaExcelParser(b"")
        self.assertIsNotNone(parser)
        self.assertEqual(parser.total_records, 0)


class TestTodopinturaImport(TransactionCase):
    """Pruebas para el modelo de importación."""

    def test_create_import_record(self):
        """Verifica que se puede crear un registro de importación."""
        import_record = self.env["todopintura.import"].create(
            {
                "name": "Test Import",
                "file_name": "test.xlsx",
            }
        )
        self.assertEqual(import_record.name, "Test Import")
        self.assertEqual(import_record.state, "draft")


class TestResPartnerExtension(TransactionCase):
    """Pruebas para la extensión de res.partner."""

    def test_partner_with_todopintura_fields(self):
        """Verifica que los campos de Todopintura se añaden a res.partner."""
        partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "todopintura_external_id": "12345",
                "todopintura_credit_limit": 1000.0,
            }
        )
        self.assertEqual(partner.todopintura_external_id, "12345")
        self.assertEqual(partner.todopintura_credit_limit, 1000.0)
