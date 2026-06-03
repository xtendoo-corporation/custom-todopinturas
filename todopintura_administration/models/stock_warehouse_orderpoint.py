# odoo/custom/src/custom-todopinturas/todopintura_administration/models/stock_warehouse_orderpoint.py
from odoo import models, fields, api
from datetime import date

class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    fixed_product_min_qty = fields.Float(
        string='Cantidad mínima fija',
        digits='Product Unit of Measure',
        default=0.0,
        help='Stock mínimo base cuando el producto no trabaja con mínimos por fechas.',
    )
    fixed_product_max_qty = fields.Float(
        string='Cantidad máxima fija',
        digits='Product Unit of Measure',
        default=0.0,
        help='Stock máximo base cuando el producto no trabaja con mínimos por fechas.',
    )

    qty_multiple = fields.Integer(
        string='Cantidad múltiplo',
        default=1,
        help='Cantidad múltiplo para el cálculo de stock mínimo y máximo.'
    )
    stock_min_dates_ids = fields.One2many('stock.min.dates', 'orderpoint_id', string='Stock Minimum Dates')
    product_min_qty = fields.Float(
        'Min Quantity', digits='Product Unit of Measure', required=True, default=0.0,
        help="When the virtual stock goes below the Min Quantity specified for this field, Odoo generates "
             "a procurement to bring the forecasted quantity to the Max Quantity.",
        compute='_compute_product_min_qty', store=True, readonly=False)
    product_max_qty = fields.Float(
        'Max Quantity', digits='Product Unit of Measure', required=True, default=0.0,
        compute='_compute_product_min_qty', store=True, readonly=False)
    is_below_min = fields.Boolean(
        string="Bajo mínimos",
        compute="_compute_is_below_min",
        store=True,
        help="Indica si la cantidad disponible es menor que la cantidad mínima"
    )

    @api.depends('product_id.qty_available', 'product_min_qty')
    def _compute_is_below_min(self):
        for record in self:
            record.is_below_min = record.product_id.qty_available < record.product_min_qty

    @api.depends(
        'stock_min_dates_ids.min_qty',
        'stock_min_dates_ids.start_date',
        'stock_min_dates_ids.end_date',
        'fixed_product_min_qty',
        'fixed_product_max_qty',
        'qty_multiple',
    )
    def _compute_product_min_qty(self):
        for orderpoint in self:
            today = date.today()
            min_date_record = orderpoint.stock_min_dates_ids.filtered(
                lambda r: r.start_date and r.end_date and r.start_date <= today < r.end_date
            )
            if min_date_record:
                orderpoint.product_min_qty = min_date_record[0].min_qty
                min_qty = min_date_record[0].min_qty
                qty_multiple = orderpoint.qty_multiple
                if qty_multiple > 0:
                    orderpoint.product_max_qty = ((min_qty // qty_multiple) + 1) * qty_multiple
                else:
                    orderpoint.product_max_qty = min_qty
            else:
                orderpoint.product_min_qty = orderpoint.fixed_product_min_qty
                orderpoint.product_max_qty = orderpoint.fixed_product_max_qty

    def action_view_stock_min_dates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Minimum Dates',
            'view_mode': 'list',
            'res_model': 'stock.min.dates',
            'domain': [('orderpoint_id', '=', self.id)],
            'context': {'default_orderpoint_id': self.id},
        }

    @api.onchange('product_min_qty')
    def _onchange_product_min_qty(self):
        if self.product_min_qty > self.product_max_qty:
            self.product_max_qty = self.product_min_qty
