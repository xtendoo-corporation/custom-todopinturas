from odoo import models, fields, api
from datetime import datetime

class SaleSession(models.Model):
    _name = 'sale.session'
    _description = 'Caja de Ventas'

    name = fields.Char('Nombre de la Caja', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company,
                                 readonly=True)
    initial_amount = fields.Float('Valor de Caja Inicial', readonly=True, default=lambda self: self.final_amount)
    final_amount = fields.Float('Valor de Caja Final', store=True)
    state = fields.Selection([
        ('open', 'Abierta'),
        ('closed', 'Cerrada')
    ], string='Estado', default='closed', readonly=True)
    open_time = fields.Datetime('Hora de Apertura', readonly=True)
    close_time = fields.Datetime('Hora de Cierre', readonly=True)
    sale_order_ids = fields.One2many('sale.order', 'sale_session_id', string='Ventas')

    def action_open_sale_box(self):
        self.initial_amount = self.final_amount
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'open.sale.session.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_session_id': self.id,
                'default_initial_amount': self.initial_amount,
            }
        }

    def action_close_sale_box(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'close.sale.session.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_session_id': self.id,
                'default_initial_amount': self.initial_amount,
                'default_final_amount': self.final_amount,
            }
        }

    def action_open_sale_session_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.session',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_view_related_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pedidos Relacionados',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('sale_session_id', '=', self.id)],
            'context': {'default_sale_session_id': self.id},
            'target': 'current',
        }
