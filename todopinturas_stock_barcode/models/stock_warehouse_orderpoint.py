# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    is_manual_min_qty = fields.Boolean(
        string='Mínimo manual',
        default=False,
        help='Indica si el stock mínimo se ha establecido manualmente.',
    )
    manual_min_qty = fields.Float(
        string='Cantidad mínima manual',
        digits='Product Unit of Measure',
        default=0.0,
        help='Stock mínimo introducido manualmente por el usuario.',
    )
    product_min_qty = fields.Float(
        compute='_compute_product_min_qty',
        inverse='_inverse_product_min_qty',
        readonly=False,
        store=True,
    )

    @api.depends(
        'is_manual_min_qty',
        'manual_min_qty',
    )
    def _compute_product_min_qty(self):
        super()._compute_product_min_qty()
        for orderpoint in self:
            if orderpoint.is_manual_min_qty:
                orderpoint.product_min_qty = orderpoint.manual_min_qty
            orderpoint.product_max_qty = orderpoint.product_min_qty

    def _inverse_product_min_qty(self):
        pass

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'product_min_qty' in vals and not self.env.context.get('import_stock_min'):
                val_min = vals.get('product_min_qty')
                if val_min != 0.0 and vals.get('is_manual_min_qty', True):
                    vals['is_manual_min_qty'] = True
                    vals['manual_min_qty'] = val_min
                vals.pop('product_min_qty')
        res = super().create(vals_list)
        if not self.env.context.get('import_stock_min'):
            self.env.add_to_compute(self._fields['product_min_qty'], res)
            self.env.add_to_compute(self._fields['product_max_qty'], res)
        return res

    def write(self, vals):
        if 'product_min_qty' in vals and not self.env.context.get('import_stock_min'):
            if vals.get('is_manual_min_qty', True):
                vals['is_manual_min_qty'] = True
                vals['manual_min_qty'] = vals['product_min_qty']
            vals.pop('product_min_qty')
        return super().write(vals)
