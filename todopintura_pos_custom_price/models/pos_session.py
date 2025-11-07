# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_category(self):
        """Método estándar para añadir campos a cargar en POS (Odoo 19)"""
        _logger.info('[CUSTOM PRICE] ===== _loader_params_product_category LLAMADO =====')
        result = super()._loader_params_product_category()
        _logger.info('[CUSTOM PRICE] Resultado super(): %s', result)

        # Asegurar que existe la estructura
        if 'search_params' not in result:
            result['search_params'] = {}
        if 'fields' not in result['search_params']:
            result['search_params']['fields'] = []

        # Añadir el campo si no existe
        if 'pos_require_custom_price' not in result['search_params']['fields']:
            result['search_params']['fields'].append('pos_require_custom_price')
            _logger.info('[CUSTOM PRICE] ✅ Campo pos_require_custom_price AÑADIDO a fields')
        else:
            _logger.info('[CUSTOM PRICE] ℹ️ Campo pos_require_custom_price ya estaba en fields')

        _logger.info('[CUSTOM PRICE] Fields finales: %s', result['search_params']['fields'])
        _logger.info('[CUSTOM PRICE] ===== FIN _loader_params_product_category =====')
        return result

    def _get_pos_ui_product_category(self, params):
        """Método alternativo para Odoo 19 (si _loader_params no funciona)"""
        _logger.info('[CUSTOM PRICE] ===== _get_pos_ui_product_category LLAMADO =====')
        _logger.info('[CUSTOM PRICE] Params recibidos: %s', params)

        # Llamar al método padre para obtener los datos base
        result = super()._get_pos_ui_product_category(params)

        _logger.info('[CUSTOM PRICE] Resultado del super: %s registros', len(result) if result else 0)

        # Añadir el campo pos_require_custom_price a cada categoría
        if result:
            for category in result:
                category_record = self.env['product.category'].browse(category['id'])
                category['pos_require_custom_price'] = category_record.pos_require_custom_price
                if category_record.pos_require_custom_price:
                    _logger.info('[CUSTOM PRICE] ⭐ Categoría %s (ID:%s): pos_require_custom_price = TRUE',
                               category.get('name'), category.get('id'))

        _logger.info('[CUSTOM PRICE] Total categorías procesadas: %s', len(result) if result else 0)
        _logger.info('[CUSTOM PRICE] ===== FIN _get_pos_ui_product_category =====')
        return result

