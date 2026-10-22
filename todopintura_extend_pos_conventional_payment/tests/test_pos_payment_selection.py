# -*- coding: utf-8 -*-
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests import tagged
from odoo.exceptions import UserError
from lxml import etree


@tagged('post_install', '-at_install')
class TestPosPaymentSelection(PosConventionalTestCommon):

    # A paid ticket may advance straight to 'done'/'invoiced' depending on
    # printing/invoicing side effects (see pos_order.py's own
    # _CONVENTIONAL_PAID_PRINTABLE_STATES); 'linked' is the correct terminal
    # state for a credit/albarán order handed off to a sale order.
    PAID_STATES = ('paid', 'done', 'invoiced')

    def setUp(self):
        super().setUp()
        # todopintura_extend_pos_conventional's pos.order.line permission
        # override rejects line creation whose price doesn't exactly match
        # the order's pricelist unless the caller carries this context flag
        # (see models/pos_order_line_permissions.py) -- these tests exercise
        # payment finalization, not that permission system, so bypass it.
        self.env = self.env(context=dict(self.env.context, allow_price_update=True))

    def _make_wizard(self, order, **vals):
        base_vals = {'order_id': order.id}
        base_vals.update(vals)
        return self.env['pos.payment.selection.wizard'].create(base_vals)

    def test_wizard_initialization(self):
        """El wizard se inicializa correctamente con los datos del pedido."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        wizard = self._make_wizard(order)

        self.assertEqual(wizard.partner_id, self.partner)
        self.assertEqual(wizard.amount_total, order.amount_total)
        self.assertEqual(wizard.amount_due, order.amount_total)

    def test_action_confirm_cash_ticket_pays_order(self):
        """Efectivo: al confirmar con importe entregado suficiente, el pedido queda pagado."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        wizard = self._make_wizard(
            order,
            operation_type='ticket',
            payment_type='cash',
            amount_tendered=order.amount_total,
        )
        self.assertTrue(wizard.has_cash_method, "El config de test debe exponer un método de pago en efectivo")

        wizard.action_confirm()

        self.assertIn(order.state, self.PAID_STATES)
        self.assertEqual(order.amount_paid, order.amount_total)

    def test_action_confirm_cash_change_is_computed(self):
        """Efectivo con importe entregado superior al total: se calcula el cambio."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        tendered = order.amount_total + 10.0
        wizard = self._make_wizard(
            order,
            operation_type='ticket',
            payment_type='cash',
            amount_tendered=tendered,
        )

        self.assertAlmostEqual(wizard.amount_change, 10.0, places=2)
        self.assertAlmostEqual(wizard.amount_change_abs, 10.0, places=2)

    def test_action_confirm_card_ticket_pays_order(self):
        """Tarjeta: al confirmar, el pedido queda pagado a través del método bancario."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        wizard = self._make_wizard(
            order,
            operation_type='ticket',
            payment_type='card',
        )
        self.assertTrue(wizard.has_card_method, "El config de test debe exponer un método de pago con tarjeta")

        wizard.action_confirm()

        self.assertIn(order.state, self.PAID_STATES)
        self.assertEqual(order.amount_paid, order.amount_total)

    def test_action_confirm_combined_pays_order(self):
        """Pago combinado: sumar varias líneas de pago hasta cubrir el total y confirmar."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        wizard = self._make_wizard(
            order,
            operation_type='ticket',
            payment_type='combined',
        )

        half = order.amount_total / 2
        wizard.write({'selected_payment_method_id': self.cash_pm.id, 'payment_amount': half})
        wizard.action_add_payment()
        wizard.write({
            'selected_payment_method_id': self.card_pm.id,
            'payment_amount': wizard.amount_due,
        })
        wizard.action_add_payment()

        self.assertAlmostEqual(wizard.amount_due, 0.0, places=2)

        wizard.action_confirm()

        self.assertIn(order.state, self.PAID_STATES)
        self.assertAlmostEqual(order.amount_paid, order.amount_total, places=2)

    def test_action_confirm_combined_insufficient_amount_raises(self):
        """Pago combinado: si el importe no cubre el total, no se debe poder confirmar."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        wizard = self._make_wizard(
            order,
            operation_type='ticket',
            payment_type='combined',
        )
        wizard.write({'selected_payment_method_id': self.cash_pm.id, 'payment_amount': 1.0})
        wizard.action_add_payment()

        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_action_confirm_delivery_albaran(self):
        """Albarán: no pasa por caja, se valida directamente como pedido a crédito."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        # Habilitamos crédito para que la política no bloquee la confirmación.
        self.partner.commercial_partner_id.write({
            'pos_credit_sale_enabled': True,
        }) if 'pos_credit_sale_enabled' in self.env['res.partner']._fields else None

        wizard = self._make_wizard(order, operation_type='delivery')

        try:
            wizard.action_confirm()
        except UserError as exc:
            # Aceptable solo si el bloqueo es por política de crédito no habilitada
            # (comportamiento correcto, no un fallo del wizard); cualquier otro
            # error debe seguir haciendo fallar el test.
            self.assertIn('crédito', str(exc).lower())
        else:
            self.assertIn(order.state, self.PAID_STATES + ('linked',))

    def test_wizard_form_layout(self):
        """Opciones como radio estándar (vertical) y avisos en un banner superior a todo el ancho."""
        arch = self.env['pos.payment.selection.wizard'].get_view(
            self.env.ref('todopintura_extend_pos_conventional_payment.view_pos_payment_selection_wizard_form').id,
        )['arch']
        doc = etree.fromstring(arch)

        for field_name in ('operation_type', 'operation_type_deposit', 'payment_type'):
            field = doc.xpath(f"//field[@name='{field_name}']")[0]
            self.assertEqual(field.get('widget'), 'radio')
            self.assertNotIn('horizontal', field.get('options') or '')
            self.assertEqual(field.get('colspan'), '2')

        banner = doc.xpath("//div[hasclass('o_todopintura_wizard_alerts')]")
        self.assertEqual(len(banner), 1)
        self.assertEqual(banner[0].getparent().tag, 'form')
        self.assertEqual(len(banner[0].xpath("./div[hasclass('alert')]")), 5)
        self.assertFalse(doc.xpath("//div[hasclass('container-fluid')]//div[hasclass('alert')]"))
        self.assertIn(
            'depósitos habilitados',
            etree.tostring(banner[0], encoding='unicode'),
        )

        combined = doc.xpath("//div[hasclass('o_todopintura_combined')]")[0]
        method = combined.xpath(".//field[@name='selected_payment_method_id']")[0]
        self.assertEqual(method.get('widget'), 'selection')
        amount = combined.xpath(".//div[hasclass('o_todopintura_cash_input_group')]/field")[0]
        self.assertEqual(amount.get('name'), 'payment_amount')
        ordered = [
            node.get('name')
            for node in combined.iter()
            if node.get('name') in ('selected_payment_method_id', 'payment_amount', 'action_add_payment', 'payment_line_ids')
        ]
        self.assertEqual(
            ordered,
            ['selected_payment_method_id', 'payment_amount', 'action_add_payment', 'payment_line_ids'],
        )

    def test_delete_combined_payment_refreshes_amount_paid(self):
        """Al eliminar un pago combinado, Pagado y Total a pagar se recalculan."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        wizard = self._make_wizard(order, operation_type='ticket', payment_type='combined')
        wizard.write({'selected_payment_method_id': self.cash_pm.id, 'payment_amount': 10.0})
        wizard.action_add_payment()
        self.assertAlmostEqual(order.amount_paid, 10.0, places=2)
        self.assertAlmostEqual(wizard.amount_due, order.amount_total - 10.0, places=2)

        action = wizard.payment_line_ids.action_delete_payment_from_wizard()
        wizard.invalidate_recordset()

        self.assertEqual(action['res_model'], 'pos.payment.selection.wizard')
        self.assertEqual(action['res_id'], wizard.id)
        self.assertEqual(action['target'], 'new')
        self.assertEqual(action['name'], 'Seleccione tipo de pago')
        self.assertAlmostEqual(wizard.payment_amount, order.amount_total, places=2)

        self.assertFalse(order.payment_ids)
        self.assertAlmostEqual(order.amount_paid, 0.0, places=2)
        self.assertAlmostEqual(wizard.amount_paid, 0.0, places=2)
        self.assertAlmostEqual(wizard.amount_due, order.amount_total, places=2)

    def test_delete_payment_legacy_action_refreshes_amount_paid(self):
        """action_delete_payment (vía contexto) también recalcula el importe pagado."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)

        wizard = self._make_wizard(order, operation_type='ticket', payment_type='combined')
        wizard.write({'selected_payment_method_id': self.cash_pm.id, 'payment_amount': 10.0})
        wizard.action_add_payment()

        wizard.with_context(payment_id=order.payment_ids.id).action_delete_payment()

        self.assertAlmostEqual(order.amount_paid, 0.0, places=2)
        self.assertAlmostEqual(wizard.amount_due, order.amount_total, places=2)

    def test_delete_payment_without_wizard_returns_nothing(self):
        """Sin wizard abierto para el pedido no se reabre nada, pero el importe se recalcula igual."""
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        order.add_payment({
            'pos_order_id': order.id,
            'amount': 10.0,
            'payment_method_id': self.cash_pm.id,
        })

        self.assertFalse(order.payment_ids.action_delete_payment_from_wizard())
        self.assertAlmostEqual(order.amount_paid, 0.0, places=2)

    def test_pay_deposit_prints_deposit_albaran_then_new_order(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order, self.product)
        location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write({
            'pos_conventional_sale_mode': 'deposit',
            'pos_credit_location_ids': [(6, 0, location.ids)],
        })

        action = order.action_pay_deposit()

        self.assertEqual(order.state, 'deposit')
        self.assertEqual(action['tag'], 'pos_conventional_print_receipt_window')
        params = action['params']
        self.assertTrue(params['is_pdf'])
        picking_ids = ','.join(str(p) for p in order.picking_ids.ids)
        self.assertEqual(
            params['url'], '/todopintura_extend_pos_conventional/albaran_pdf/%s' % picking_ids
        )
        self.assertEqual(params['next_action']['tag'], 'pos_conventional_new_order')
