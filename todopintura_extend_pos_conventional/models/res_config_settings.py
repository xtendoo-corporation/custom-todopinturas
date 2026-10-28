# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Mismo nombre y parámetro que en todopintura_pos_custom para que ambos
    # módulos puedan convivir compartiendo el ajuste.
    pos_load_all_pricelists = fields.Boolean(
        string="Cargar todas las tarifas",
        config_parameter="point_of_sale.pos_load_all_pricelists",
        help="Todas las tarifas de la compañía están disponibles en el POS, "
        "sin tener que añadirlas una a una a cada caja.",
    )
    pos_conventional_source_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Ubicación de la caja POS conventional",
        related="pos_config_id.conventional_source_location_id",
        readonly=True,
    )

