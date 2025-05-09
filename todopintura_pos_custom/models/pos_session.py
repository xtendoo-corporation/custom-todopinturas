from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_stock_picking_type(self):
        result = super()._loader_params_stock_picking_type()
        result['search_params']['fields'].extend(['default_location_src_id', 'default_location_dest_id'])
        return result

