# En wizards/stock_count_compare_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from datetime import datetime

class StockCountCompare(models.TransientModel):
    _name = 'stock.count.compare.wizard'
    _description = 'Comparación de Conteos de Inventario'

    count_ids = fields.Many2many('stock.count', string='Conteos', readonly=True)
    count_count = fields.Integer('Número de conteos', compute='_compute_count_count')
    line_ids = fields.One2many('stock.count.compare.line.wizard', 'compare_id', string='Líneas de comparación')

    @api.depends('count_ids')
    def _compute_count_count(self):
        for record in self:
            record.count_count = len(record.count_ids)

    def action_apply_real_quantities(self):
        # Verificar que sean conteos pares
        if self.count_count % 2 != 0:
            raise ValidationError(_("El número de conteos debe ser par."))

        # Verificar que todas las líneas tengan una cantidad real establecida
        lines_without_real_quantity = self.line_ids.filtered(lambda l: not l.real_quantity and l.real_quantity != 0)
        if lines_without_real_quantity:
            products = lines_without_real_quantity.mapped('product_id.name')
            raise ValidationError(_("Debe establecer una cantidad real para todos los productos. "
                                    "Productos faltantes: %s") % ", ".join(products))

        # Obtener la ubicación directamente del primer conteo
        if not self.count_ids:
            raise ValidationError(_("No hay conteos seleccionados."))

        location = self.count_ids[0].location_id
        if not location:
            raise ValidationError(_("No se pudo determinar la ubicación de stock."))

        # Obtener todos los productos incluidos en la comparación
        products_in_compare = self.line_ids.mapped('product_id.id')

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

        # Buscar todos los quants en la ubicación que no están en la comparación
        other_quants = self.env['stock.quant'].search([
            ('location_id', '=', location.id),
            ('product_id', 'not in', products_in_compare),
            ('quantity', '>', 0)
        ])

        # Establecer a 0 la cantidad de inventario para estos productos
        if other_quants:
            other_quants.write({
                'inventory_quantity': 0,
                'inventory_diff_quantity': -1 * other_quants.mapped('quantity')
            })

        self.count_ids.write({
            'state': 'done',
            'date_end': fields.Datetime.now()
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
    count_value_ids = fields.One2many('stock.count.value.wizard', 'line_id', string='Valores por conteo')
    match = fields.Boolean('Coincide', compute='_compute_match', store=True)
    real_quantity = fields.Float('Cantidad Real', readonly=False, store=True,
                              digits='Product Unit of Measure')
    count_values_display = fields.Text(string="Valores de conteo", compute="_compute_count_values_display")

    @api.depends('count_value_ids')
    def _compute_count_values_display(self):
        for line in self:
            values = []
            for value in line.count_value_ids:
                values.append(f"{value.count_id.name}: {value.quantity} ({value.scan_datetime.strftime('%d/%m/%Y %H:%M')})")
            line.count_values_display = "\n".join(values)

    @api.depends('count_value_ids.quantity')
    def _compute_match(self):
        for line in self:
            values = line.count_value_ids.mapped('quantity')
            # Hay coincidencia si todos los valores son iguales
            line.match = len(set(values)) <= 1 if values else False
            if line.match and values:
                line.real_quantity = values[0]

    def action_view_count_details(self):
        return {
            'name': _('Detalles de Conteo para %s') % self.product_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.count.value.wizard',
            'view_mode': 'list',
            'domain': [('id', 'in', self.count_value_ids.ids)],
            'target': 'dialog',  # Usar 'dialog' en lugar de 'new'
            'flags': {'mode': 'readonly'},
            'context': {
                'create': False,
                'edit': False
            }
        }


class StockCountValue(models.TransientModel):
    _name = 'stock.count.value.wizard'
    _description = 'Valor de Conteo'

    line_id = fields.Many2one('stock.count.compare.line.wizard', string='Línea de comparación')
    count_id = fields.Many2one('stock.count', string='Conteo', readonly=True)
    quantity = fields.Float('Cantidad', readonly=True, digits='Product Unit of Measure')
    scan_datetime = fields.Datetime('Fecha escaneo', readonly=True)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.count_id.name}: {record.quantity}"
            result.append((record.id, name))
        return result
