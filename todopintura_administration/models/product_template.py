from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    invoice_description = fields.Char(string="Invoice description", help="Invoice description")

    @api.model
    def default_get(self, fields_list):
        res = super(ProductTemplate, self).default_get(fields_list)
        if 'route_ids' in fields_list:
            routes = self.env['stock.route'].search([('product_selectable', '=', True)])
            res['route_ids'] = [(6, 0, routes.ids)]
        return res

