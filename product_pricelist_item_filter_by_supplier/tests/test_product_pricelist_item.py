from odoo.tests.common import TransactionCase
import logging

class TestProductPricelistItem(TransactionCase):
    def setUp(self):
        super().setUp()

        # Crear un proveedor (partner)
        self.supplier = self.env["res.partner"].create({"name": "Proveedor 1"})

        # Crear otro proveedor para el caso de no coincidencia
        self.other_supplier = self.env["res.partner"].create({"name": "Proveedor 2"})

        # Crear una plantilla de producto con purchase_line_warn
        self.product_template = self.env["product.template"].create({
            "name": "Producto de prueba",
        })

        # Crear un producto basado en la plantilla
        self.product = self.env["product.product"].create({
            "name": "Producto de prueba",
            "product_tmpl_id": self.product_template.id,
        })

        # Asignar el proveedor al producto
        self.env["product.supplierinfo"].create({
            "partner_id": self.supplier.id,
            "product_tmpl_id": self.product.product_tmpl_id.id,
        })

        # Crear una lista de precios
        self.pricelist = self.env["product.pricelist"].create({"name": "Lista de precios de prueba"})

    def test_compute_price_no_supplier(self):
        """Caso 1: Proveedor vacío, el cálculo de precio debe proceder normalmente"""
        pricelist_item = self.env["product.pricelist.item"].create({
            "pricelist_id": self.pricelist.id,
            "applied_on": "1_product",
            "product_tmpl_id": self.product_template.id,
            "compute_price": "fixed",
            "fixed_price": 100.0,
            "filter_supplier_id": False,  # No tiene proveedor asignado
        })

        price = pricelist_item._compute_price(self.product, 1, self.product.uom_id, None)
        self.assertEqual(price, 100.0, "El precio debería ser 100.0 sin proveedor asignado")
        logging.info("Test 'test_compute_price_no_supplier' passed: Price is 100.0 when no supplier is assigned")

    def test_compute_price_with_matching_supplier(self):
        """Caso 2: Proveedor coincide, el cálculo de precio debe proceder normalmente"""
        pricelist_item = self.env["product.pricelist.item"].create({
            "pricelist_id": self.pricelist.id,
            "applied_on": "1_product",
            "product_tmpl_id": self.product_template.id,
            "compute_price": "fixed",
            "fixed_price": 150.0,
            "filter_supplier_id": self.supplier.id,  # Proveedor coincide
        })

        price = pricelist_item._compute_price(self.product, 1, self.product.uom_id, None)
        self.assertEqual(price, 150.0, "El precio debería ser 150.0 cuando el proveedor coincide")
        logging.info("Test 'test_compute_price_with_matching_supplier' passed: Price is 150.0 when supplier matches")

    def test_compute_price_with_non_matching_supplier(self):
        """Caso 3: Proveedor no coincide, el precio no debería aplicarse"""
        pricelist_item = self.env["product.pricelist.item"].create({
            "pricelist_id": self.pricelist.id,
            "applied_on": "1_product",
            "product_tmpl_id": self.product_template.id,
            "compute_price": "fixed",
            "fixed_price": 200.0,
            "filter_supplier_id": self.other_supplier.id,  # Proveedor NO coincide
        })

        price = pricelist_item._compute_price(self.product, 1, self.product.uom_id, None)
        self.assertEqual(price, 0.0, "El precio debería ser 0.0 cuando el proveedor no coincide")
        logging.info("Test 'test_compute_price_with_non_matching_supplier' passed: Price is 0.0 when supplier doesn't match")
