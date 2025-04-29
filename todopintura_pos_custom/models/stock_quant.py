# Añade esto a models/stock_quant.py

from odoo import models, api, fields


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def get_product_quantities_in_location(self, product_ids, location_id):
        """Obtiene las cantidades disponibles de productos en una ubicación específica"""
        if not product_ids or not location_id:
            return []

        quants = self.search([
            ('product_id', 'in', product_ids),
            ('location_id', '=', location_id),
        ])

        result = []
        for quant in quants:
            result.append({
                'product_id': quant.product_id.id,
                'product_name': quant.product_id.display_name,
                'quantity': quant.quantity,
                'available_quantity': quant.available_quantity,
                'reserved_quantity': quant.reserved_quantity
            })

        # Añadir productos que no tienen quants con cantidad 0
        existing_product_ids = [item['product_id'] for item in result]
        for product_id in product_ids:
            if product_id not in existing_product_ids:
                product = self.env['product.product'].browse(product_id)
                result.append({
                    'product_id': product_id,
                    'product_name': product.display_name,
                    'quantity': 0,
                    'available_quantity': 0,
                    'reserved_quantity': 0
                })

        return result
