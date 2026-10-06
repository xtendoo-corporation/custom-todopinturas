# -*- coding: utf-8 -*-
from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_invoice_lines_values(self, line_values, pos_line, move_type):
        # Las facturas generadas desde la caja reflejan en la cuenta analítica
        # de la caja (igual que los apuntes de cierre de sesión).
        res = super()._get_invoice_lines_values(line_values, pos_line, move_type)
        account = self.config_id.analytic_account_id
        if account and not res.get("display_type") and not res.get("analytic_distribution"):
            res["analytic_distribution"] = {str(account.id): 100.0}
        return res
