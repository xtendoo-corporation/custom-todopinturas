from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    main_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Almacén principal',
        help='Almacén principal asociado al usuario',
    )

