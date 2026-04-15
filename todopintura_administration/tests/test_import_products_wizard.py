import base64

from odoo.tests.common import TransactionCase


class TestImportProductsWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.wizard = self.env['import.products.wizard'].create({
            'file': base64.b64encode(b'dummy'),
            'file_name': 'dummy.xlsx',
        })

    def test_ensure_default_tariffs_creates_all_pricelists(self):
        tariffs = self.wizard._ensure_default_tariffs()

        self.assertEqual(set(tariffs.keys()), {f'Tarifa {i}' for i in range(1, 8)})
        for name, pricelist in tariffs.items():
            self.assertTrue(pricelist, name)
            self.assertEqual(pricelist.name, name)

    def test_create_or_update_tariffs_uses_percentage_when_discount_available(self):
        product = self.env['product.template'].create({
            'name': 'Producto Test',
            'default_code': 'PT-001',
            'list_price': 10.0,
        })

        self.wizard.create_or_update_tariffs(product, 12.5, 7.0, 'Tarifa 2')

        pricelist = self.env['product.pricelist'].search([('name', '=', 'Tarifa 2')], limit=1)
        item = self.env['product.pricelist.item'].search([
            ('pricelist_id', '=', pricelist.id),
            ('product_tmpl_id', '=', product.id),
        ], limit=1)

        self.assertTrue(item)
        self.assertEqual(item.compute_price, 'percentage')
        self.assertEqual(item.percent_price, 7.0)

    def test_create_or_update_tariffs_skips_line_when_discount_is_empty(self):
        product = self.env['product.template'].create({
            'name': 'Producto Sin Precio',
            'default_code': 'PT-NOPRICE',
            'list_price': 10.0,
        })

        self.wizard.create_or_update_tariffs(product, 12.5, None, 'Tarifa 3')

        pricelist = self.env['product.pricelist'].search([('name', '=', 'Tarifa 3')], limit=1)
        item = self.env['product.pricelist.item'].search([
            ('pricelist_id', '=', pricelist.id),
            ('product_tmpl_id', '=', product.id),
        ], limit=1)

        self.assertFalse(item)

    def test_create_or_update_tariffs_removes_existing_line_when_discount_becomes_empty(self):
        product = self.env['product.template'].create({
            'name': 'Producto Limpieza',
            'default_code': 'PT-CLEAN',
            'list_price': 10.0,
        })
        pricelist = self.env['product.pricelist'].create({'name': 'Tarifa Limpieza'})
        item = self.env['product.pricelist.item'].create({
            'pricelist_id': pricelist.id,
            'product_tmpl_id': product.id,
            'applied_on': '1_product',
            'compute_price': 'percentage',
            'percent_price': 8.0,
        })

        self.wizard.create_or_update_tariffs(product, 12.5, None, 'Tarifa Limpieza')

        self.assertFalse(item.exists())

    def test_create_or_update_tariffs_skips_line_when_discount_is_zero(self):
        product = self.env['product.template'].create({
            'name': 'Producto Precio Cero',
            'default_code': 'PT-ZERO',
            'list_price': 10.0,
        })

        self.wizard.create_or_update_tariffs(product, 12.5, 0.0, 'Tarifa 4')

        pricelist = self.env['product.pricelist'].search([('name', '=', 'Tarifa 4')], limit=1)
        item = self.env['product.pricelist.item'].search([
            ('pricelist_id', '=', pricelist.id),
            ('product_tmpl_id', '=', product.id),
        ], limit=1)

        self.assertFalse(item)

    def test_create_or_update_tariffs_ignores_price_and_uses_discount(self):
        product = self.env['product.template'].create({
            'name': 'Producto Precio Base',
            'default_code': 'PT-BASE',
            'list_price': 10.0,
        })

        self.wizard.create_or_update_tariffs(product, None, 12.0, 'Tarifa 5')

        pricelist = self.env['product.pricelist'].search([('name', '=', 'Tarifa 5')], limit=1)
        item = self.env['product.pricelist.item'].search([
            ('pricelist_id', '=', pricelist.id),
            ('product_tmpl_id', '=', product.id),
        ], limit=1)

        self.assertTrue(item)
        self.assertEqual(item.compute_price, 'percentage')
        self.assertEqual(item.percent_price, 12.0)

    def test_duplicate_barcode_is_cleared_on_second_product(self):
        self.env['product.template'].create({
            'name': 'Producto Original',
            'default_code': 'PT-ORIG',
            'list_price': 10.0,
            'barcode': '1234567890',
        })

        product = self.wizard._create_or_update_product({
            'name': 'Producto Duplicado',
            'default_code': 'PT-DUP',
            'list_price': 15.0,
            'barcode': '1234567890',
        })

        self.assertTrue(product)
        self.assertFalse(product.barcode)

    def test_duplicate_barcode_is_cleared_when_updating_existing_product(self):
        self.env['product.template'].create({
            'name': 'Producto Original',
            'default_code': 'PT-ORIG-2',
            'list_price': 10.0,
            'barcode': '8428073036474',
        })
        existing_product = self.env['product.template'].create({
            'name': 'Producto a Actualizar',
            'default_code': 'PT-UPD',
            'list_price': 15.0,
        })

        product = self.wizard._create_or_update_product({
            'name': 'Producto a Actualizar',
            'default_code': 'PT-UPD',
            'list_price': 20.0,
            'barcode': '8428073036474',
        })

        self.assertEqual(product.id, existing_product.id)
        self.assertFalse(product.barcode)

