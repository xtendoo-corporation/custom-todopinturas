# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_conventional_source_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Ubicación de la caja POS conventional",
        related="pos_config_id.conventional_source_location_id",
        readonly=True,
    )

