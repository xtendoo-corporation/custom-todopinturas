# En wizards/stock_count_compare_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class StockCountCompare(models.TransientModel):
    _name = 'stock.count.compare.wizard'
    _description = 'Comparación de Conteos de Inventario'

    count_id_1 = fields.Many2one('stock.count', string='Primer Conteo', readonly=True)
    count_id_2 = fields.Many2one('stock.count', string='Segundo Conteo', readonly=True)
    line_ids = fields.One2many('stock.count.compare.line.wizard', 'compare_id', string='Líneas de comparación')

    def action_apply_real_quantities(self):
        """
        Transfiere las cantidades reales establecidas en el wizard a los quants de inventario
        actualizando directamente inventory_quantity.
        """
        # Verificar que todas las líneas tengan una cantidad real establecida
        lines_without_real_quantity = self.line_ids.filtered(lambda l: not l.real_quantity and l.real_quantity != 0)
        if lines_without_real_quantity:
            products = lines_without_real_quantity.mapped('product_id.name')
            raise ValidationError(_("Debe establecer una cantidad real para todos los productos. "
                                    "Productos faltantes: %s") % ", ".join(products))

        # Obtener la ubicación directamente del primer conteo
        location = self.count_id_1.location_id
        if not location:
            raise ValidationError(_("No se pudo determinar la ubicación de stock."))

        # Para cada línea, actualizar el quant correspondiente
        for line in self.line_ids:
            quants = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', location.id),
            ])

            if quants:
                quants.write({'inventory_quantity': line.real_quantity})
                quants.write({'inventory_diff_quantity': line.real_quantity - quants.quantity})
            else:
                self.env['stock.quant'].create({
                    'product_id': line.product_id.id,
                    'location_id': location.id,
                    'inventory_quantity': line.real_quantity,
                    'inventory_diff_quantity': line.real_quantity
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Éxito"),
                'message': _("Las cantidades de inventario han sido actualizadas."),
                'sticky': False,
            }
        }

class StockCountCompareLine(models.TransientModel):
    _name = 'stock.count.compare.line.wizard'
    _description = 'Línea de Comparación de Conteos'

    compare_id = fields.Many2one('stock.count.compare.wizard', string='Comparación')
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    quantity_1 = fields.Float('Cantidad en Conteo 1', readonly=True, digits='Product Unit of Measure')
    quantity_2 = fields.Float('Cantidad en Conteo 2', readonly=True, digits='Product Unit of Measure')
    match = fields.Boolean('Coincide', compute='_compute_match', store=True)
    real_quantity = fields.Float('Cantidad Real', readonly=False, store=True,
                                 digits='Product Unit of Measure')

    @api.depends('quantity_1', 'quantity_2')
    def _compute_match(self):
        for line in self:
            line.match = float_compare(line.quantity_1, line.quantity_2, precision_rounding=0.001) == 0
            # Si coinciden y está activado el auto-rellenado, actualiza real_quantity
            if line.match:
                line.real_quantity = line.quantity_1

