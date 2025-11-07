# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    # Este método ya debería existir por el otro archivo, pero lo redefinimos aquí por claridad
    pos_require_custom_price = fields.Boolean(
        string='Requiere Precio Personalizado en POS',
        default=False,
        help='Si está marcado, al escanear un producto de esta categoría en el POS, '
             'se solicitará introducir un precio personalizado.'
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Método para Odoo 19 - añadir campos a cargar en POS"""
        _logger.info('='*80)
        _logger.info('[CUSTOM PRICE] ===== _load_pos_data_fields EJECUTADO =====')
        _logger.info('[CUSTOM PRICE] Config ID: %s', config_id)

        result = super()._load_pos_data_fields(config_id)
        _logger.info('[CUSTOM PRICE] Fields del super: %s', result)

        # Añadir nuestro campo personalizado si no está
        if isinstance(result, list) and 'pos_require_custom_price' not in result:
            result.append('pos_require_custom_price')
            _logger.info('[CUSTOM PRICE] ✅ Campo pos_require_custom_price AÑADIDO a la lista')
        elif isinstance(result, set) and 'pos_require_custom_price' not in result:
            result.add('pos_require_custom_price')
            _logger.info('[CUSTOM PRICE] ✅ Campo pos_require_custom_price AÑADIDO al set')

        _logger.info('[CUSTOM PRICE] Fields finales: %s', result)
        _logger.info('[CUSTOM PRICE] ===== FIN _load_pos_data_fields =====')
        _logger.info('='*80)
        return result

    @api.model
    def _load_pos_data(self, data):
        """Método alternativo para Odoo 19 si _load_pos_data_fields no funciona"""
        _logger.info('='*80)
        _logger.info('[CUSTOM PRICE] ===== _load_pos_data EJECUTADO =====')
        _logger.info('[CUSTOM PRICE] Data keys: %s', data.keys() if hasattr(data, 'keys') else type(data))

        result = super()._load_pos_data(data)

        # Asegurar que el campo se incluya en el resultado
        if isinstance(result, dict):
            for category in result.get('data', []):
                if isinstance(category, dict) and 'id' in category:
                    cat_record = self.browse(category['id'])
                    category['pos_require_custom_price'] = cat_record.pos_require_custom_price
                    if cat_record.pos_require_custom_price:
                        _logger.info('[CUSTOM PRICE] ⭐ Categoría %s (ID:%s) con pos_require_custom_price=True',
                                   category.get('name'), category.get('id'))

        _logger.info('[CUSTOM PRICE] ===== FIN _load_pos_data =====')
        _logger.info('='*80)
        return result

