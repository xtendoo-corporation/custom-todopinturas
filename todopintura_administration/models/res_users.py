from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    main_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Almacén principal',
        help='Almacén principal asociado al usuario',
    )

    pos_can_edit_price = fields.Boolean(
        string='Puede modificar precios en TPV',
        default=False,
        help='Permite al usuario cambiar manualmente el precio de líneas en el Punto de Venta',
    )
