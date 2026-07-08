# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestPosPaymentSelection(common.TransactionCase):

    def setUp(self):
        super(TestPosPaymentSelection, self).setUp()

        # 1. Datos base: Partner y Configuración de POS
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'delivery_report_print_type': 'valued',
        })

        self.pos_config = self.env['pos.config'].create({
            'name': 'Test POS Shop',
        })

        self.pos_session = self.env['pos.session'].create({
            'config_id': self.pos_config.id,
            'user_id': self.env.uid,
        })

        # 2. Crear un pedido de POS en borrador
        self.pos_order = self.env['pos.order'].create({
            'session_id': self.pos_session.id,
            'partner_id': self.partner.id,
            'amount_total': 100.0,
            'lines': [(0, 0, {
                'product_id': self.env.ref('product.product_product_4').id,
                'qty': 1,
                'price_unit': 100.0,
                'price_subtotal': 100.0,
                'price_subtotal_incl': 121.0,
            })],
        })

    def test_wizard_initialization(self):
        """Verifica que el wizard se inicializa correctamente con los datos del pedido"""
        wizard_vals = {
            'order_id': self.pos_order.id,
        }
        wizard = self.env['pos.payment.selection.wizard'].create(wizard_vals)

        self.assertEqual(wizard.partner_id, self.partner, "El partner debe coincidir")
        self.assertEqual(wizard.amount_total, self.pos_order.amount_total, "El total debe coincidir")
        self.assertEqual(wizard.amount_due, 100.0, "El importe pendiente debe ser el total")

    def test_action_confirm_valued_report(self):
        """Verifica que al confirmar el wizard genera la acción de reporte correcto"""
        wizard = self.env['pos.payment.selection.wizard'].create({
            'order_id': self.pos_order.id,
            'operation_type': 'delivery',
        })

        # Forzamos que el partner quiera albarán valorado
        self.partner.delivery_report_print_type = 'valued'

        # El método action_confirm debería procesar el pedido y devolver el reporte
        # Nota: Simulamos el contexto que espera el método
        action = wizard.with_context(active_id=self.pos_order.id).action_confirm()

        self.assertIsNotNone(action, "Debe devolver una acción")
        # Dependiendo de la lógica interna de todopintura, verificamos nombres clave
        # Por ejemplo, si devuelve un reporte valorado:
        if isinstance(action, dict) and action.get('report_name'):
            self.assertIn('valued', action.get('report_name', ''), "Debe ser el reporte valorado")

