# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    def get_product_info_pos(self, price, quantity, pos_config_id):
        self.ensure_one()
        config = self.env['pos.config'].browse(pos_config_id)

        # Estructura mínima para all_prices
        all_prices = {
            'price_without_tax': price,
            'price_with_tax': price,
            'tax_details': [],
        }

        # Obtener solo el precio de la tarifa actual
        current_pricelist = config.pricelist_id
        pricelist_list = [{
            'name': current_pricelist.name,
            'price': price
        }]

        # Obtener ubicaciones internas (stock)
        locations = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', config.company_id.id),
        ])

        # Para mantener la estructura existente, usamos el mismo formato pero con ubicaciones
        warehouse_list = []
        for loc in locations:
            qty_available = self.with_context(location=loc.id).qty_available
            # Solo incluir ubicaciones con stock (opcional)
            if qty_available > 0:
                warehouse_list.append({
                    'id': loc.id,
                    'name': loc.complete_name,
                    'available_quantity': qty_available,
                    'forecasted_quantity': self.with_context(location=loc.id).virtual_available,
                    'uom': self.uom_name
                })

        # Si no hay ubicaciones con stock, mostrar todas las ubicaciones
        if not warehouse_list:
            warehouse_list = [
                {'id': loc.id,
                 'name': loc.complete_name,
                 'available_quantity': self.with_context(location=loc.id).qty_available,
                 'forecasted_quantity': self.with_context(location=loc.id).virtual_available,
                 'uom': self.uom_name}
                for loc in locations
            ]

        return {
            'all_prices': all_prices,
            'pricelists': pricelist_list,
            'warehouses': warehouse_list,
            'suppliers': [],
            'variants': []
        }
