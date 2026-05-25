from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    id_todopinturas = fields.Char(string='ID Todopinturas', help='Identificador interno de Todopinturas para el almacén')

