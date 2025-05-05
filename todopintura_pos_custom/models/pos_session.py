from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_pricelist_item(self):
        result = super()._loader_params_product_pricelist_item()
        if 'filter_supplier_id' not in result['search_params']['fields']:
            result['search_params']['fields'].append('filter_supplier_id')
        return result

    def _get_pos_ui_product_pricelist_item(self, params):
        result = super()._get_pos_ui_product_pricelist_item(params)
        for item in result:
            if item.get('filter_supplier_id'):
                supplier = self.env['res.partner'].browse(item['filter_supplier_id'])
                item['filter_supplier_id'] = {
                    'id': supplier.id,
                    'name': supplier.name,
                }
                print(f"Filter supplier ID procesado: {item['filter_supplier_id']}")
        return result

    def get_pos_ui_product_pricelist_item_by_product(self, product_tmpl_ids, product_ids, config_id):
        result = super().get_pos_ui_product_pricelist_item_by_product(product_tmpl_ids, product_ids, config_id)

        # Procesar filter_supplier_id para los elementos de la lista de precios
        pricelist_items = result.get('product.pricelist.item', [])
        for item in pricelist_items:
            if item.get('filter_supplier_id'):
                supplier = self.env['res.partner'].browse(item['filter_supplier_id'])
                item['filter_supplier_id'] = {
                    'id': supplier.id,
                    'name': supplier.name,
                }
                print(f"Filter supplier ID procesado en by_product: {item['filter_supplier_id']}")

        return result

    def _loader_params_stock_picking_type(self):
        result = super()._loader_params_stock_picking_type()
        result['search_params']['fields'].extend(['default_location_src_id', 'default_location_dest_id'])
        return result

