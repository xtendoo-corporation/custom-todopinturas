# -*- coding: utf-8 -*-

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_stock_location(self):
        result = super()._loader_params_stock_location()
        result["search_params"]["fields"].append("pos_receipt_name")
        return result

    def _loader_params_stock_warehouse(self):
        result = super()._loader_params_stock_warehouse()
        result["search_params"]["fields"].append("lot_stock_id")
        return result

    def _loader_params_pos_order_line(self):
        result = super()._loader_params_pos_order_line()
        result["search_params"]["fields"].append("pickup_warehouse_id")
        return result
