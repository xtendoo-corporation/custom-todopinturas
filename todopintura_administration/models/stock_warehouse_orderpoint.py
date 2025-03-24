from odoo import models, fields, api
from datetime import date

class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    stock_min_dates_ids = fields.One2many('stock.min.dates', 'orderpoint_id', string='Stock Minimum Dates')
    product_min_qty = fields.Float(
        'Min Quantity', digits='Product Unit of Measure', required=True, default=0.0,
        help="When the virtual stock goes below the Min Quantity specified for this field, Odoo generates "
             "a procurement to bring the forecasted quantity to the Max Quantity.",
        compute='_compute_product_min_qty', store=True)

    @api.depends('stock_min_dates_ids')
    def _compute_product_min_qty(self):
        for orderpoint in self:
            today = date.today()
            min_date_record = orderpoint.stock_min_dates_ids.filtered(
                lambda r: r.start_date <= today <= r.end_date
            )
            if min_date_record:
                orderpoint.product_min_qty = min_date_record[0].min_qty
            else:
                orderpoint.product_min_qty = 0.0
