# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    manual_price = fields.Boolean(
        related='product_tmpl_id.manual_price',
        string='Precio Manual',
        store=False,
        help='Indica si el producto requiere ingreso manual de precio en el TPV'
    )

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

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'display_name', 'lst_price', 'categ_id', 'pos_categ_ids', 'taxes_id', 'barcode',
            'name',
            'default_code', 'to_weight', 'uom_id', 'product_tmpl_id', 'tracking',
            'type', 'is_storable',
            'available_in_pos', 'attribute_line_ids', 'active', 'image_128', 'combo_ids',
            'product_template_variant_value_ids', 'manual_price',
        ]

    @api.model
    def get_partner_prices(self, product_ids, partner_id, pricelist_id=False):
        """Obtiene los precios que deberían tener los productos según las reglas de precio"""
        result = {}
        partner = self.env['res.partner'].browse(partner_id)
        pricelist = pricelist_id and self.env['product.pricelist'].browse(
            pricelist_id) or partner.property_product_pricelist

        if not pricelist:
            return result

        products = self.browse(product_ids)
        prices = pricelist.get_products_price(products, [1.0] * len(products), partner)

        return prices
