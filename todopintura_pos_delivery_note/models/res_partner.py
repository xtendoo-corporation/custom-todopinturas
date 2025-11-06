# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    valued_picking = fields.Boolean(
        string="Mostrar Precios en Albarán",
        default=False,
        help="Si está activado, el albarán mostrará los precios y totales"
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Añadir campo valued_picking al POS"""
        fields = super()._load_pos_data_fields(config_id)

        if 'valued_picking' not in fields:
            fields.append('valued_picking')

        return fields

