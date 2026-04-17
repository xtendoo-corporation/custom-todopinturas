import base64

from odoo.tests.common import TransactionCase


class TestImportCategoriesWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.wizard = self.env['import.categories.wizard'].create({
            'file': base64.b64encode(b'dummy'),
            'file_name': 'dummy.xlsx',
        })

    def test_reimport_updates_existing_categories_without_duplicates(self):
        initial_rows = [
            (10000, 'Pinturas'),
            (10100, 'Interior'),
            (10101, 'Lavable'),
        ]
        updated_rows = [
            (10000, 'Pinturas y barnices'),
            (10100, 'Interior premium'),
            (10101, 'Lavable mate'),
        ]

        self.wizard._import_category_rows(initial_rows)
        self.wizard._import_category_rows(updated_rows)

        categories = self.env['pos.category'].search([
            ('referencia_todopintura', 'in', [10000, 10100, 10101]),
        ])

        self.assertEqual(len(categories), 3)

        root = self.env['pos.category'].search([('referencia_todopintura', '=', 10000)], limit=1)
        child = self.env['pos.category'].search([('referencia_todopintura', '=', 10100)], limit=1)
        leaf = self.env['pos.category'].search([('referencia_todopintura', '=', 10101)], limit=1)

        self.assertEqual(root.name, 'Pinturas y barnices')
        self.assertEqual(child.name, 'Interior premium')
        self.assertEqual(leaf.name, 'Lavable mate')
        self.assertFalse(root.parent_id)
        self.assertEqual(child.parent_id, root)
        self.assertEqual(leaf.parent_id, child)
