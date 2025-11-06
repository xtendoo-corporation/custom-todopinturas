# -*- coding: utf-8 -*-
from odoo import models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    def _load_pos_data(self, data):
        """Cargar ubicaciones en el POS"""
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return self.search_read(domain, fields, load=False)

    def _load_pos_data_domain(self, data):
        """Define el dominio para cargar ubicaciones en el POS"""
        return [('usage', '=', 'internal')]

    def _load_pos_data_fields(self, config_id):
        """Define los campos de stock.location que se cargan en el POS"""
        return ['id', 'name', 'complete_name', 'usage', 'location_id']

