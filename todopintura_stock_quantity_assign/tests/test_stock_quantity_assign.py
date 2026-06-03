# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestStockQuantityAssign(TransactionCase):
    """
    Tests para verificar que las cantidades en pickings de compra
    no se rellenan automáticamente.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear un proveedor
        cls.supplier = cls.env['res.partner'].create({
            'name': 'Test Supplier',
            'supplier_rank': 1,
        })

        # Crear una categoría de producto
        cls.product_category = cls.env['product.category'].create({
            'name': 'Test Category',
        })

        # Crear productos
        cls.product_1 = cls.env['product.product'].create({
            'name': 'Test Product 1',
            'type': 'product',
            'categ_id': cls.product_category.id,
            'list_price': 100.0,
            'standard_price': 50.0,
        })

        cls.product_2 = cls.env['product.product'].create({
            'name': 'Test Product 2',
            'type': 'product',
            'categ_id': cls.product_category.id,
            'list_price': 200.0,
            'standard_price': 100.0,
        })

        # Crear ubicaciones
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')

    def test_01_purchase_order_creates_moves_with_zero_quantity(self):
        """
        Test: Al confirmar una orden de compra, los movimientos de stock
        deben crearse con quantity = 0.
        """
        # Crear orden de compra
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_1.id,
                    'product_qty': 10.0,
                    'price_unit': 50.0,
                }),
                (0, 0, {
                    'product_id': self.product_2.id,
                    'product_qty': 5.0,
                    'price_unit': 100.0,
                }),
            ],
        })

        # Confirmar la orden de compra
        purchase_order.button_confirm()

        # Obtener el picking generado
        picking = purchase_order.picking_ids
        self.assertTrue(picking, "Debe haberse creado un picking")

        # Verificar que los movimientos tienen quantity = 0
        for move in picking.move_ids:
            self.assertEqual(
                move.quantity,
                0.0,
                f"El movimiento del producto {move.product_id.name} "
                f"debe tener quantity = 0, pero tiene {move.quantity}"
            )

    def test_02_move_confirm_maintains_zero_quantity(self):
        """
        Test: Al confirmar un movimiento de compra, la quantity debe
        permanecer en 0.
        """
        # Crear orden de compra
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_1.id,
                    'product_qty': 15.0,
                    'price_unit': 50.0,
                }),
            ],
        })

        # Confirmar la orden de compra
        purchase_order.button_confirm()

        # Obtener el picking y los movimientos
        picking = purchase_order.picking_ids
        moves = picking.move_ids

        # Confirmar los movimientos (si no están confirmados)
        if moves.filtered(lambda m: m.state == 'draft'):
            moves.filtered(lambda m: m.state == 'draft')._action_confirm()

        # Verificar que la quantity sigue siendo 0
        for move in moves:
            self.assertEqual(
                move.quantity,
                0.0,
                f"Después de confirmar, el movimiento debe mantener quantity = 0"
            )

    def test_03_move_assign_maintains_zero_quantity(self):
        """
        Test: Al asignar un movimiento de compra, la quantity debe
        permanecer en 0.
        """
        # Crear orden de compra
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_1.id,
                    'product_qty': 20.0,
                    'price_unit': 50.0,
                }),
            ],
        })

        # Confirmar la orden de compra
        purchase_order.button_confirm()

        # Obtener el picking y los movimientos
        picking = purchase_order.picking_ids
        moves = picking.move_ids

        # Asignar los movimientos
        picking.action_assign()

        # Verificar que la quantity sigue siendo 0
        for move in moves:
            self.assertEqual(
                move.quantity,
                0.0,
                f"Después de asignar, el movimiento debe mantener quantity = 0"
            )

    def test_04_manual_quantity_update_works(self):
        """
        Test: El usuario debe poder actualizar manualmente la quantity.
        """
        # Crear orden de compra
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_1.id,
                    'product_qty': 10.0,
                    'price_unit': 50.0,
                }),
            ],
        })

        # Confirmar la orden de compra
        purchase_order.button_confirm()

        # Obtener el picking y los movimientos
        picking = purchase_order.picking_ids
        move = picking.move_ids[0]

        # Verificar que quantity es 0
        self.assertEqual(move.quantity, 0.0)

        # Actualizar manualmente la quantity
        manual_quantity = 8.0
        move.write({'quantity': manual_quantity})

        # Verificar que se actualizó correctamente
        self.assertEqual(
            move.quantity,
            manual_quantity,
            f"La quantity manual debe ser {manual_quantity}"
        )

    def test_05_non_purchase_moves_not_affected(self):
        """
        Test: Los movimientos que no están relacionados con compras
        no deben verse afectados por el módulo.
        """
        # Crear un movimiento de stock manual (no relacionado con compra)
        move = self.env['stock.move'].create({
            'name': 'Test Manual Move',
            'product_id': self.product_1.id,
            'product_uom_qty': 25.0,
            'product_uom': self.product_1.uom_id.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
        })

        # Confirmar el movimiento
        move._action_confirm()

        # Este movimiento NO está relacionado con una compra,
        # por lo que podría tener quantity automática (según configuración de Odoo)
        # Lo importante es verificar que nuestro módulo no interfiere
        # Solo verificamos que no hay errores y el movimiento se confirma
        self.assertIn(
            move.state,
            ['confirmed', 'assigned', 'waiting'],
            "El movimiento manual debe poder confirmarse sin errores"
        )

    def test_06_multiple_products_in_purchase(self):
        """
        Test: Orden de compra con múltiples productos debe tener
        todos los movimientos con quantity = 0.
        """
        # Crear orden de compra con 3 productos
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_1.id,
                    'product_qty': 10.0,
                    'price_unit': 50.0,
                }),
                (0, 0, {
                    'product_id': self.product_2.id,
                    'product_qty': 20.0,
                    'price_unit': 100.0,
                }),
                (0, 0, {
                    'product_id': self.product_1.id,
                    'product_qty': 5.0,
                    'price_unit': 45.0,
                }),
            ],
        })

        # Confirmar la orden de compra
        purchase_order.button_confirm()

        # Obtener el picking
        picking = purchase_order.picking_ids

        # Verificar que hay movimientos
        self.assertTrue(
            len(picking.move_ids) >= 2,
            "Debe haber al menos 2 movimientos (pueden fusionarse productos iguales)"
        )

        # Verificar que TODOS los movimientos tienen quantity = 0
        for move in picking.move_ids:
            self.assertEqual(
                move.quantity,
                0.0,
                f"Todos los movimientos deben tener quantity = 0, "
                f"pero {move.product_id.name} tiene {move.quantity}"
            )

    def test_07_barcode_scanning_updates_quantity(self):
        """
        Test: El escaneo de códigos de barras debe actualizar la cantidad.
        """
        # Crear producto con código de barras
        product_with_barcode = self.env['product.product'].create({
            'name': 'Test Product With Barcode',
            'type': 'product',
            'categ_id': self.product_category.id,
            'barcode': '1234567890123',
            'list_price': 100.0,
            'standard_price': 50.0,
        })

        # Crear orden de compra
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [
                (0, 0, {
                    'product_id': product_with_barcode.id,
                    'product_qty': 10.0,
                    'price_unit': 50.0,
                }),
            ],
        })

        # Confirmar la orden de compra
        purchase_order.button_confirm()

        # Obtener el picking
        picking = purchase_order.picking_ids
        self.assertTrue(picking, "Debe haberse creado un picking")

        # Verificar que quantity inicial es 0
        move = picking.move_ids.filtered(lambda m: m.product_id == product_with_barcode)
        self.assertEqual(move.quantity, 0.0, "La cantidad inicial debe ser 0")

        # Escanear el código de barras del producto 3 veces
        for i in range(3):
            result = picking.on_barcode_scanned(product_with_barcode.barcode)
            # Verificar que no hay warning
            self.assertFalse(
                result and result.get('warning'),
                f"El escaneo {i+1} no debería devolver warning"
            )

        # Refrescar el movimiento desde la base de datos
        move.invalidate_recordset(['quantity'])

        # Verificar que la cantidad se ha actualizado correctamente
        self.assertEqual(
            move.quantity,
            3.0,
            "Después de escanear 3 veces, la cantidad debe ser 3"
        )

    def test_08_barcode_scanning_product_not_in_picking(self):
        """
        Test: El escaneo de un producto que no está en el picking debe mostrar warning.
        """
        # Crear productos con códigos de barras
        product_in_picking = self.env['product.product'].create({
            'name': 'Product In Picking',
            'type': 'product',
            'categ_id': self.product_category.id,
            'barcode': '1111111111111',
            'list_price': 100.0,
            'standard_price': 50.0,
        })

        product_not_in_picking = self.env['product.product'].create({
            'name': 'Product Not In Picking',
            'type': 'product',
            'categ_id': self.product_category.id,
            'barcode': '2222222222222',
            'list_price': 100.0,
            'standard_price': 50.0,
        })

        # Crear orden de compra solo con product_in_picking
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [
                (0, 0, {
                    'product_id': product_in_picking.id,
                    'product_qty': 5.0,
                    'price_unit': 50.0,
                }),
            ],
        })

        # Confirmar la orden de compra
        purchase_order.button_confirm()

        # Obtener el picking
        picking = purchase_order.picking_ids

        # Escanear el producto que NO está en el picking
        result = picking.on_barcode_scanned(product_not_in_picking.barcode)

        # Verificar que se devuelve un warning
        self.assertTrue(
            result and result.get('warning'),
            "El escaneo de un producto no esperado debe devolver warning"
        )
        self.assertIn(
            'no esperado',
            result['warning']['message'].lower(),
            "El mensaje debe indicar que el producto no es esperado"
        )

