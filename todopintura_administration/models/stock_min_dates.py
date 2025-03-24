from odoo import models, fields

class StockMinDates(models.Model):
    _name = 'stock.min.dates'
    _description = 'Stock Minimum Dates'

    min_qty = fields.Integer(string='Cantidad Mínima', required=True)
    start_date = fields.Date(string='Fecha Inicio', required=True)
    end_date = fields.Date(string='Fecha Fin', required=True)
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string='Orderpoint', ondelete='cascade')
