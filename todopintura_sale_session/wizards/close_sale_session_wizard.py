from odoo import models, fields, api
from datetime import datetime

class CloseSaleSessionWizard(models.TransientModel):
    _name = 'close.sale.session.wizard'
    _description = 'Wizard para Cerrar Caja de Ventas'

    sale_session_id = fields.Many2one('sale.session', string='Caja de Ventas', required=True)
    initial_amount = fields.Float('Valor de Caja Inicial', readonly=True)
    final_amount = fields.Float('Valor de Caja Final', required=True)

    def action_close_sale_box(self):
        self.sale_session_id.write({
            'state': 'closed',
            'close_time': datetime.now(),
            'final_amount': self.final_amount,
        })
        self.env['sale.session.history'].create({
            'sale_session_id': self.sale_session_id.id,
            'open_time': self.sale_session_id.open_time,
            'close_time': self.sale_session_id.close_time,
            'initial_amount': self.initial_amount,
            'final_amount': self.final_amount,
        })
