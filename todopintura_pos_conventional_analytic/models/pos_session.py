# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_analytic_distribution(self):
        """Distribución analítica de esta sesión, según la caja (pos.config).

        Formato esperado por `account.move.line.analytic_distribution`:
        {"<analytic_account_id>": <percentage>}.
        """
        account = self.config_id.analytic_account_id
        if not account:
            return False
        return {str(account.id): 100.0}

    def _get_sale_vals(self, key, sale_vals):
        # Línea de venta (ingreso): mismo hook que usa el core para construir
        # cada apunte de venta al cerrar la sesión.
        vals = super()._get_sale_vals(key, sale_vals)
        distribution = self._get_analytic_distribution()
        if distribution:
            vals["analytic_distribution"] = distribution
        return vals

    def _get_stock_expense_vals(self, exp_account, amount, amount_converted):
        # Línea de coste de venta (gasto): para que el análisis por caja
        # incluya también el coste, no sólo el ingreso.
        vals = super()._get_stock_expense_vals(exp_account, amount, amount_converted)
        distribution = self._get_analytic_distribution()
        if distribution:
            vals["analytic_distribution"] = distribution
        return vals
