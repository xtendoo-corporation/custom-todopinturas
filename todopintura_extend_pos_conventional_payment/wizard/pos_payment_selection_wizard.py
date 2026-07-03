# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PosPaymentSelectionWizard(models.TransientModel):
    _name = "pos.payment.selection.wizard"
    _description = "Selección de tipo de pago POS"

    order_id = fields.Many2one("pos.order", string="Pedido", required=True)
    state = fields.Selection([
        ('doc_selection', 'Document Selection'),
        ('payment_selection', 'Payment Selection')
    ], default='doc_selection')

    document_type = fields.Selection([
        ('ticket', 'Ticket'),
        ('factura_simplified', 'Factura Simplificada'),
        ('factura_a4', 'Factura A4')
    ])

    partner_id = fields.Many2one("res.partner", related="order_id.partner_id")
    config_id = fields.Many2one("pos.config", related="order_id.config_id")
    payment_method_ids = fields.Many2many("pos.payment.method", related="config_id.payment_method_ids")
    show_deposit_button = fields.Boolean(related="order_id.show_deposit_button")
    partner_credit_available = fields.Boolean(related="order_id.partner_credit_available")

    # Campos técnicos para botones estáticos de métodos de pago comunes
    has_cash_method = fields.Boolean(compute="_compute_payment_methods")
    has_card_method = fields.Boolean(compute="_compute_payment_methods")
    cash_method_id = fields.Many2one("pos.payment.method", compute="_compute_payment_methods")
    card_method_id = fields.Many2one("pos.payment.method", compute="_compute_payment_methods")

    @api.depends('payment_method_ids')
    def _compute_payment_methods(self):
        for wizard in self:
            cash = wizard.payment_method_ids.filtered(lambda m: m.type == 'cash' or m.is_cash_count)[:1]
            card = wizard.payment_method_ids.filtered(lambda m: m.type == 'bank' or m.journal_id.type == 'bank')[:1]
            wizard.has_cash_method = bool(cash)
            wizard.cash_method_id = cash.id
            wizard.has_card_method = bool(card)
            wizard.card_method_id = card.id

    def action_ticket(self):
        self.ensure_one()
        self.document_type = 'factura_simplified'
        self.state = 'payment_selection'
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_pago_combinado(self):
        self.ensure_one()
        # Aplicamos el tipo de documento seleccionado antes de abrir el popup
        if self.document_type == 'ticket':
            self.order_id.write({
                'to_invoice': False,
                'is_a4_invoice': False,
                'is_l10n_es_simplified_invoice': False,
            })
        elif self.document_type == 'factura_simplified':
             self.order_id.write({
                'to_invoice': True,
                'is_a4_invoice': False,
                'is_l10n_es_simplified_invoice': True,
            })
        elif self.document_type == 'factura_a4':
             self.order_id.write({
                'to_invoice': True,
                'is_a4_invoice': True,
                'is_l10n_es_simplified_invoice': False,
            })
        return self.order_id.action_open_payment_popup()

    def action_pago_metodo(self):
        self.ensure_one()
        payment_method_id = self.env.context.get('payment_method_id')
        if not payment_method_id:
            return False

        # Aplicamos el tipo de documento seleccionado antes de procesar el pago rápido
        if self.document_type == 'ticket':
            self.order_id.write({
                'to_invoice': False,
                'is_a4_invoice': False,
                'is_l10n_es_simplified_invoice': False,
            })
        elif self.document_type == 'factura_simplified':
             self.order_id.write({
                'to_invoice': True,
                'is_a4_invoice': False,
                'is_l10n_es_simplified_invoice': True,
            })
        elif self.document_type == 'factura_a4':
             self.order_id.write({
                'to_invoice': True,
                'is_a4_invoice': True,
                'is_l10n_es_simplified_invoice': False,
            })

        return self.order_id.action_pos_convention_pay_with_method(payment_method_id)

    def action_factura(self):
        self.ensure_one()
        self.document_type = 'factura_a4'
        self.state = 'payment_selection'
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_factura_a4(self):
        self.ensure_one()
        self.document_type = 'factura_a4'
        self.state = 'payment_selection'
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_cancel_payment_step(self):
        self.ensure_one()
        self.state = 'doc_selection'
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_pago_efectivo(self):
        self.ensure_one()
        if self.cash_method_id:
            # Reutiliza action_pago_metodo con el contexto adecuado
            return self.with_context(payment_method_id=self.cash_method_id.id).action_pago_metodo()
        return False

    def action_pago_tarjeta(self):
        self.ensure_one()
        if self.card_method_id:
            # Reutiliza action_pago_metodo con el contexto adecuado
            return self.with_context(payment_method_id=self.card_method_id.id).action_pago_metodo()
        return False

    def action_albaran(self):
        self.ensure_one()
        return self.order_id.action_pay_account()

    def action_deposito(self):
        self.ensure_one()
        return self.order_id.action_pay_deposit()

    def action_credito(self):
        self.ensure_one()
        return self.order_id.action_pay_account()

    def get_payment_methods(self):
        self.ensure_one()
        return [{
            'id': method.id,
            'name': method.name
        } for method in self.payment_method_ids]
