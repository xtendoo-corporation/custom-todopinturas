# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    pos_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="res_users_pos_employee_rel",
        column1="user_id",
        column2="employee_id",
        string="Empleados del TPV",
        copy=False,
        help="Empleados que pueden identificarse con su PIN en las cajas de este "
        "usuario. Varios empleados comparten el usuario de la caja.",
    )


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    pos_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="res_users_pos_employee_rel",
        column1="employee_id",
        column2="user_id",
        string="Usuarios del TPV",
        copy=False,
        help="Usuarios (cajas) en los que este empleado puede identificarse con su PIN.",
    )
