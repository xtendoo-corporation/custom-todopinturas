# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Obtener la lista original de campos
        fields_list = super()._load_pos_data_fields(config_id)

        # Añadir el campo seller_ids para obtener los proveedores
        fields_list.append('seller_ids')
        print("Campos de datos del POS cargados (Productos):", fields_list)
        return fields_list
