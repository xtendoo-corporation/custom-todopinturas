# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models

PIN_HELP = (
    "Pide el PIN del empleado al abrir la caja y tras cada venta (solo modo no "
    "táctil). Varios empleados comparten el usuario de la caja."
)


class PosConfig(models.Model):
    _inherit = "pos.config"

    pos_force_employee_login_after_order = fields.Boolean(
        string="Pedir PIN del empleado", help=PIN_HELP
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_force_employee_login_after_order = fields.Boolean(
        string="Pedir PIN del empleado", help=PIN_HELP
    )
