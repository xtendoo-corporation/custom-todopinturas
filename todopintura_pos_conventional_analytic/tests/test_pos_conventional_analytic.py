# -*- coding: utf-8 -*-
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosConventionalAnalytic(PosConventionalTestCommon):

    def setUp(self):
        super().setUp()
        # todopintura_extend_pos_conventional's pos.order.line permission
        # override rejects line creation whose price doesn't exactly match
        # the order's pricelist unless the caller carries this context flag
        # (see that module's models/pos_order_line_permissions.py) -- these
        # tests exercise session closing/analytic distribution, not that
        # permission system, so bypass it.
        self.env = self.env(context=dict(self.env.context, allow_price_update=True))
        self.analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Plan Test Cajas',
        })
        self.analytic_account = self.env['account.analytic.account'].create({
            'name': 'Caja Test Analytic',
            'plan_id': self.analytic_plan.id,
        })

    def _close_session_with_paid_order(self, config, payment_method=None):
        session = self._open_session(config)
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        self._add_payment(order, payment_method=payment_method or self.cash_pm, amount=order.amount_total)
        order.state = 'paid'
        session._create_account_move()
        return session

    def test_sale_and_expense_lines_get_the_pos_config_analytic_account(self):
        """Las líneas de venta (y de coste, si hay valoración) de una sesión
        cerrada deben llevar la cuenta analítica configurada en su caja."""
        self.pos_config.analytic_account_id = self.analytic_account
        session = self._close_session_with_paid_order(self.pos_config)

        sale_lines = session.move_id.line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertTrue(sale_lines, "Debe haberse generado al menos una línea de venta")
        expected = {str(self.analytic_account.id): 100.0}
        for line in sale_lines:
            self.assertEqual(
                line.analytic_distribution, expected,
                "La línea de venta debe llevar la cuenta analítica de la caja",
            )

    def test_no_analytic_account_configured_does_not_force_distribution(self):
        """Sin cuenta analítica configurada en la caja, el comportamiento no
        cambia respecto al núcleo (no se fuerza ninguna distribución)."""
        self.assertFalse(self.pos_config.analytic_account_id)
        session = self._close_session_with_paid_order(self.pos_config)

        sale_lines = session.move_id.line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertTrue(sale_lines)
        for line in sale_lines:
            self.assertFalse(
                line.analytic_distribution,
                "Sin cuenta configurada no debe forzarse ninguna distribución analítica",
            )

    def test_two_configs_with_different_analytic_accounts_stay_independent(self):
        """Dos cajas con cuentas analíticas distintas no se mezclan entre sí."""
        other_account = self.env['account.analytic.account'].create({
            'name': 'Otra Caja Analytic',
            'plan_id': self.analytic_plan.id,
        })
        other_pm = self._make_fresh_cash_pm(name='Efectivo Otra Caja')
        other_config = self.env['pos.config'].create({
            'name': 'Otra Caja Test',
            'payment_method_ids': [(6, 0, [other_pm.id])],
            'analytic_account_id': other_account.id,
        })
        self.pos_config.analytic_account_id = self.analytic_account

        session_a = self._close_session_with_paid_order(self.pos_config)
        session_b = self._close_session_with_paid_order(other_config, payment_method=other_pm)

        lines_a = session_a.move_id.line_ids.filtered(lambda l: l.display_type == 'product')
        lines_b = session_b.move_id.line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertTrue(lines_a and lines_b)
        for line in lines_a:
            self.assertEqual(line.analytic_distribution, {str(self.analytic_account.id): 100.0})
        for line in lines_b:
            self.assertEqual(line.analytic_distribution, {str(other_account.id): 100.0})
