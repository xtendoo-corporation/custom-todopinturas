# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    is_commercial = fields.Boolean(
        string="¿Es comercial?",
        copy=False,
        help="Los comerciales solo ven sus propios presupuestos y pedidos y no pueden "
        "confirmar un presupuesto a pedido de venta: solo enviarlo al cliente.",
    )
    allowed_warehouse_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        relation="res_users_allowed_warehouse_rel",
        column1="user_id",
        column2="warehouse_id",
        string="Almacenes/tiendas permitidos",
        copy=False,
        help="Si se informa, el usuario solo ve y opera los traspasos, pedidos "
        "de venta y ventas de TPV de estos almacenes. Vacío = sin restricción.",
    )
