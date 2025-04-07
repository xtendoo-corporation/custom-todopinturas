from odoo import models, fields, api

class OpenSaleSessionWizard(models.TransientModel):
    _name = 'open.sale.session.wizard'
    _description = 'Asistente para Abrir Caja de Ventas'

    sale_session_id = fields.Many2one('sale.session', string='Caja de Ventas', required=True)
    initial_amount = fields.Float('Valor de Caja Inicial', required=True)

    def action_open_session(self):
        self.sale_session_id.write({
            'state': 'open',
            'open_time': fields.Datetime.now(),
            'initial_amount': self.initial_amount,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Presupuestos',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.sale_session_id.company_id.id)],
            'context': {
                'default_sale_session_id': self.sale_session_id.id,
            },
            'target': 'current',
        }
