# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class StockCount(models.Model):
    _name = 'stock.count'
    _description = 'Conteo de Inventario'
    _order = 'date_start desc'

    name = fields.Char('Referencia', readonly=True, copy=False, default='Nuevo')
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    date_start = fields.Datetime('Fecha/Hora Inicio', required=True, default=fields.Datetime.now)
    date_end = fields.Datetime('Fecha/Hora Fin')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Completado'),
        ('cancel', 'Cancelado')
    ], string='Estado', default='draft')
    zone = fields.Text('Zona', help='Descripción de la zona contada')
    location_id = fields.Many2one('stock.location', string='Ubicación', required=True,
                                domain=[('usage', '=', 'internal')])
    line_ids = fields.One2many('stock.count.line', 'count_id', string='Líneas de conteo')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.count') or 'Nuevo'
        return super().create(vals_list)

    def action_start(self):
        return {
            'name': _('Conteo de productos'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.count.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_count_id': self.id},
        }

    def action_compare_counts(self):
        if len(self) < 2 or len(self) % 2 != 0:
            raise ValidationError(_("Debe seleccionar un número par de conteos (al menos dos) para comparar."))

        # Crear wizard con todos los conteos seleccionados
        wizard = self.env['stock.count.compare.wizard'].create({
            'count_ids': [(6, 0, self.ids)],
        })

        # Obtener todos los productos que aparecen en cualquiera de los conteos
        all_products = self.env['product.product']
        for count in self:
            all_products |= count.line_ids.mapped('product_id')

        # Crear líneas de comparación
        compare_lines = []
        for product in all_products:
            line_vals = {
                'product_id': product.id,
                'count_value_ids': [],
            }

            # Crear un valor para cada conteo
            for count in self:
                # Obtener líneas correspondientes a este producto en el conteo actual
                count_lines = count.line_ids.filtered(lambda l: l.product_id.id == product.id)
                quantity = sum(count_lines.mapped('quantity'))

                # Obtener la fecha más reciente para este producto en este conteo
                scan_datetime = count_lines and max(count_lines.mapped('scan_datetime')) or False

                # Agregar valor para este conteo
                line_vals['count_value_ids'].append((0, 0, {
                    'count_id': count.id,
                    'quantity': quantity,
                    'scan_datetime': scan_datetime,
                }))

            compare_lines.append((0, 0, line_vals))

        wizard.write({'line_ids': compare_lines})

        return {
            'name': _('Comparación de Conteos'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.count.compare.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
    def action_done(self):
        self.write({
            'state': 'done',
            'date_end': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})


class StockCountLine(models.Model):
    _name = 'stock.count.line'
    _description = 'Línea de Conteo de Inventario'

    count_id = fields.Many2one('stock.count', string='Conteo', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    quantity = fields.Float('Unidades', default=1.0, required=True)
    scan_datetime = fields.Datetime('Fecha y hora de escaneo', default=fields.Datetime.now, readonly=True)
