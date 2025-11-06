# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    voucher = fields.Boolean(string="Vale")
    assigned_persons = fields.Boolean(string="Personas asignadas")
    assigned_persons_info = fields.Text(
        string="Información de personas asignadas",
        help="Ingrese detalles sobre las personas asignadas a este cliente"
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Añadir campos de vales y personas asignadas al POS"""
        fields = super()._load_pos_data_fields(config_id)

        custom_fields = [
            'voucher',
            'assigned_persons',
            'assigned_persons_info',
        ]

        for field in custom_fields:
            if field not in fields:
                fields.append(field)

        return fields

