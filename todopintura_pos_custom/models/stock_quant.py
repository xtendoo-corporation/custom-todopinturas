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

    @api.model
    def get_products_in_all_locations(self, product_ids, location_ids):
        """Obtiene las cantidades disponibles de varios productos en múltiples ubicaciones

        Args:
            product_ids: Lista de IDs de productos
            location_ids: Lista de IDs de ubicaciones

        Returns:
            Lista de diccionarios con la información de stock para cada combinación
            producto-ubicación que exista
        """
        if not product_ids or not location_ids:
            return []

        # Buscar todos los quants que coinciden con los productos y ubicaciones
        quants = self.search([
            ('product_id', 'in', product_ids),
            ('location_id', 'in', location_ids),
        ])

        result = []
        # Primero procesamos los quants existentes
        for quant in quants:
            result.append({
                'product_id': quant.product_id.id,
                'product_name': quant.product_id.display_name,
                'location_id': quant.location_id.id,
                'location_name': quant.location_id.display_name,
                'quantity': quant.quantity,
                'available_quantity': quant.available_quantity,
                'reserved_quantity': quant.reserved_quantity
            })

        # Luego añadimos entradas con cantidad 0 para combinaciones de producto-ubicación que no existan
        # Esto permite tener una lista completa para mostrar en la interfaz
        existing_combinations = {(item['product_id'], item['location_id']) for item in result}

        Product = self.env['product.product']
        Location = self.env['stock.location']
        products = Product.browse(product_ids)
        locations = Location.browse(location_ids)

        for product in products:
            for location in locations:
                if (product.id, location.id) not in existing_combinations:
                    result.append({
                        'product_id': product.id,
                        'product_name': product.display_name,
                        'location_id': location.id,
                        'location_name': location.display_name,
                        'quantity': 0,
                        'available_quantity': 0,
                        'reserved_quantity': 0
                    })

        return result
