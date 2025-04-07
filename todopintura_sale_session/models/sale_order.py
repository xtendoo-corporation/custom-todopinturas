from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_session_id = fields.Many2one('sale.session', string='Caja de Ventas')

    @api.model
    def create(self, vals):
        if 'default_sale_session_id' in self.env.context:
            vals['sale_session_id'] = self.env.context['default_sale_session_id']
        return super(SaleOrder, self).create(vals)
