# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PosPaymentSelectionWizard(models.TransientModel):
    _name = "pos.payment.selection.wizard"
    _description = "Selección de tipo de pago POS"

    order_id = fields.Many2one("pos.order", string="Pedido", required=True)

    def action_ticket(self):
        self.ensure_one()
        self.order_id.write({'to_invoice': False, 'is_a4_invoice': False})
        return self.order_id.action_open_payment_popup()

    def action_factura(self):
        self.ensure_one()
        self.order_id.write({'to_invoice': True, 'is_a4_invoice': True})
        return self.order_id.action_open_payment_popup()

    def action_albaran(self):
        self.ensure_one()
        return self.order_id.action_pay_account()

    def action_deposito(self):
        self.ensure_one()
        return self.order_id.action_pay_deposit()

    def action_credito(self):
        self.ensure_one()
        return self.order_id.action_pay_account()
