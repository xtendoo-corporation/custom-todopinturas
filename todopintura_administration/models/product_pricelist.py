from odoo import models, api, fields
from odoo.tools.translate import _


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"


    @api.model
    def action_view_pricelist_lines(self):
        """Return an action opening the product.pricelist.item records filtered by this pricelist.

        We open the standard tree/form view for product.pricelist.item so the user can use the search
        panel to filter by product, product template or category.
        """
        self.ensure_one()
        action = {
            'name': _('Líneas de Tarifa'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.pricelist.item',
            'view_mode': 'tree,form',
            'domain': [('pricelist_id', '=', self.id)],
            'context': {'default_pricelist_id': self.id, 'search_default_filter_pricelist': True},
            'target': 'current',
        }
        return action


