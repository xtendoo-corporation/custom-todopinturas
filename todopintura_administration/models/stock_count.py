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
        ('in_progress', 'En Progreso'),
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
        self.write({
            'state': 'in_progress',
            'date_start': fields.Datetime.now(),
        })

        # Abrir el wizard para comenzar a añadir productos
        return {
            'name': _('Conteo de productos'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.count.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_count_id': self.id},
        }

    def action_resume(self):
        """Reanudar un conteo pausado"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise ValidationError(_("Solo se pueden reanudar conteos que estén pausados."))

        # Abrimos el wizard para continuar el conteo
        return {
            'name': _('Conteo de productos'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.count.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_count_id': self.id},
        }
    def action_compare_counts(self):
        if len(self) != 2:
            raise ValidationError(_("Debe seleccionar exactamente dos conteos para comparar."))

        wizard = self.env['stock.count.compare.wizard'].create({
            'count_id_1': self[0].id,
            'count_id_2': self[1].id,
        })

        # Obtener todos los productos que aparecen en ambos conteos
        products_1 = self[0].line_ids.mapped('product_id')
        products_2 = self[1].line_ids.mapped('product_id')
        all_products = products_1 | products_2

        # Crear líneas de comparación
        compare_lines = []
        for product in all_products:
            quantity_1 = sum(self[0].line_ids.filtered(lambda l: l.product_id == product).mapped('quantity'))
            quantity_2 = sum(self[1].line_ids.filtered(lambda l: l.product_id == product).mapped('quantity'))
            compare_lines.append((0, 0, {
                'product_id': product.id,
                'quantity_1': quantity_1,
                'quantity_2': quantity_2,
            }))

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
