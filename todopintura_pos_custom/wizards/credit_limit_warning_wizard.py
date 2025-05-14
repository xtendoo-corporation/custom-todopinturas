from odoo import models, api, fields, _


class CreditLimitWarningWizard(models.TransientModel):
    _name = 'credit.limit.warning.wizard'
    _description = 'Advertencia de Límite de Crédito'

    partner_id = fields.Many2one('res.partner', 'Cliente', readonly=True)
    sale_order_id = fields.Many2one('sale.order', 'Presupuesto', readonly=True)
    credit_limit = fields.Float('Límite de Crédito', readonly=True)
    credit_used = fields.Float('Crédito Usado', readonly=True)
    order_amount = fields.Float('Importe del Pedido', readonly=True)
    total_credit = fields.Float('Crédito Total', readonly=True)

    def action_continue(self):
        """Continúa con la confirmación del pedido"""
        return self.sale_order_id.with_context(bypass_credit_check=True).action_confirm()

    def action_cancel(self):
        """Cancela la acción de confirmación"""
        return {'type': 'ir.actions.act_window_close'}
