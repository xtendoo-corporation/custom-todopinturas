from odoo import models, fields

class SaleSessionHistory(models.Model):
    _name = 'sale.session.history'
    _description = 'Historial de Caja de Ventas'

    sale_session_id = fields.Many2one('sale.session', string='Caja de Ventas', required=True)
    open_time = fields.Datetime('Hora de Apertura', required=True)
    close_time = fields.Datetime('Hora de Cierre', required=True)
    initial_amount = fields.Float('Valor de Caja Inicial', required=True)
    final_amount = fields.Float('Valor de Caja Final', required=True)
