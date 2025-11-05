# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        """Cargar parámetros de datos para el POS"""
        params = super()._load_data_params(config_id)

        # Agregar stock.location a los modelos a cargar
        params['stock.location'] = {
            'domain': [('usage', '=', 'internal')],
            'fields': ['id', 'name', 'complete_name', 'usage', 'location_id'],
        }

        return params


