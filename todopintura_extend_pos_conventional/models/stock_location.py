# -*- coding: utf-8 -*-

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    pos_receipt_name = fields.Char(
        string="Nombre a mostrar en ticket de pos",
        help="Si se rellena, este nombre aparecerá en el ticket del TPV debajo del producto.",
    )

    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        if "pos_receipt_name" not in res:
            res.append("pos_receipt_name")
        return res
