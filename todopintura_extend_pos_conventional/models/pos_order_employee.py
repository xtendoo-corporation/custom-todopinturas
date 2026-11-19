# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model_create_multi
    def create(self, vals_list):
        """El pedido creado desde el TPV convencional lleva como cajero al empleado
        que se identificó con su PIN en la sesión."""
        for vals in vals_list:
            if not vals.get("employee_id") and vals.get("session_id"):
                session = self.env["pos.session"].sudo().browse(vals["session_id"])
                if session.employee_id:
                    vals["employee_id"] = session.employee_id.id
        return super().create(vals_list)
