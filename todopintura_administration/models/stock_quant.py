from odoo import fields, models, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    inventory_quantity_1 = fields.Float(
        'Cantidad contada 1', digits='Product Unit of Measure',
        help="La cantidad contada del producto (primer conteo)."
    )

    inventory_quantity_2 = fields.Float(
        'Cantidad contada 2', digits='Product Unit of Measure',
        help="La cantidad contada del producto (segundo conteo)."
    )

    @api.onchange('inventory_quantity_1', 'inventory_quantity_2')
    def _onchange_counted_quantities(self):
        """Si ambas cantidades contadas coinciden, se asigna ese valor a inventory_quantity"""
        for quant in self:
            if quant.inventory_quantity_1 and quant.inventory_quantity_2 and \
                quant.inventory_quantity_1 == quant.inventory_quantity_2:
                quant.inventory_quantity = quant.inventory_quantity_1
