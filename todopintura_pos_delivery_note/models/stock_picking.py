# -*- coding: utf-8 -*-
from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_report_lang(self):
        """Obtiene el idioma para el reporte"""
        self.ensure_one()
        if self.partner_id and self.partner_id.lang:
            return self.partner_id.lang
        return self.env.lang or 'es_ES'

    def should_print_delivery_address(self):
        """Determina si se debe imprimir la dirección de entrega"""
        self.ensure_one()
        return self.picking_type_code == 'outgoing' and self.partner_id

