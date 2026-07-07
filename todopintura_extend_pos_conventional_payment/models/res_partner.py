# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
class ResPartner(models.Model):
    _inherit = 'res.partner'
    pos_order_credit_count = fields.Integer(
        string='Pedidos TPV Credito',
        compute='_compute_pos_order_credit_deposit_count'
    )
    pos_order_deposit_count = fields.Integer(
        string='Pedidos TPV Deposito',
        compute='_compute_pos_order_credit_deposit_count'
    )
    def _compute_pos_order_credit_deposit_count(self):
        for partner in self:
            partner.pos_order_credit_count = self.env['pos.order'].search_count([
                ('partner_id', '=', partner.id),
                ('state', '=', 'linked')
            ])
            partner.pos_order_deposit_count = self.env['pos.order'].search_count([
                ('partner_id', '=', partner.id),
                ('state', '=', 'deposit')
            ])
    def action_view_pos_credit_orders(self):
        self.ensure_one()
        return {
            'name': _('Pedidos de TPV (Credito)'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('state', '=', 'linked')],
            'context': {'default_partner_id': self.id},
        }
    def action_view_pos_deposit_orders(self):
        self.ensure_one()
        return {
            'name': _('Pedidos de TPV (Deposito)'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('state', '=', 'deposit')],
            'context': {'default_partner_id': self.id},
        }
