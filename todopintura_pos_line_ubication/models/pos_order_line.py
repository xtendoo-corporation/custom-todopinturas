from odoo import fields, models, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    location_id = fields.Many2one(
        'stock.location',
        string='Ubicación',
        domain=[('usage', '=', 'internal')],
        help='Ubicación de inventario específica para esta línea de pedido'
    )
