# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosPaymentSelectionWizard(models.TransientModel):
    _name = "pos.payment.selection.wizard"
    _description = "Selección de tipo de pago POS"

    order_id = fields.Many2one("pos.order", string="Pedido", required=True)
    state = fields.Selection([
        ('doc_selection', 'Document Selection'),
        ('payment_selection', 'Payment Selection')
    ], default='doc_selection')

    operation_type = fields.Selection([
        ('ticket', 'Factura simplificada'),
        ('invoice', 'Factura A4'),
        ('delivery', 'Albarán'),
        ('deposit', 'Depósito'),
    ], string="¿Qué desea hacer?", default='ticket')

    payment_type = fields.Selection([
        ('cash', 'Efectivo'),
        ('card', 'Tarjeta'),
        ('combined', 'Pago combinado'),
    ], string="Método de Pago", default='cash')

    document_type = fields.Selection([
        ('ticket', 'Ticket'),
        ('factura_simplified', 'Factura Simplificada'),
        ('factura_a4', 'Factura A4')
    ])

    partner_id = fields.Many2one("res.partner", related="order_id.partner_id")
    config_id = fields.Many2one("pos.config", related="order_id.config_id")
    payment_method_ids = fields.Many2many("pos.payment.method", related="config_id.payment_method_ids")
    show_deposit_button = fields.Boolean(related="order_id.show_deposit_button")
    partner_deposit_enabled = fields.Boolean(related="order_id.partner_deposit_enabled")
    partner_deposit_available = fields.Boolean(related="order_id.partner_deposit_available")
    partner_deposit_warning_message = fields.Text(related="order_id.partner_deposit_warning_message")
    partner_credit_available = fields.Boolean(related="order_id.partner_credit_available")
    partner_credit_limit_exceeded = fields.Boolean(compute="_compute_credit_status")

    # Campos de detalle de crédito para avisos
    partner_credit_limit = fields.Monetary(related="order_id.partner_credit_limit_amount")
    partner_current_due = fields.Monetary(related="order_id.partner_current_total_due")
    partner_total_due_after = fields.Monetary(related="order_id.partner_total_due_after_order")

    @api.depends('order_id', 'operation_type')
    def _compute_credit_status(self):
        for wizard in self:
            if wizard.operation_type == 'delivery':
                policy = wizard.order_id._get_conventional_credit_policy_data()
                wizard.partner_credit_limit_exceeded = policy.get('limit_exceeded', False)
            else:
                wizard.partner_credit_limit_exceeded = False

    # Campos de importes para la vista unificada
    amount_total = fields.Monetary(related="order_id.amount_total", readonly=True)
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    amount_paid = fields.Monetary(related="order_id.amount_paid", readonly=True)
    amount_due = fields.Monetary(compute="_compute_payment_amounts")
    amount_tendered = fields.Monetary(string="Importe Entregado")
    amount_change = fields.Monetary(string="Diferencia", compute="_compute_payment_amounts")
    amount_change_abs = fields.Monetary(string="Cambio", compute="_compute_payment_amounts")

    # Campos para Gestión de Pagos Combinados en la misma ventana
    selected_payment_method_id = fields.Many2one("pos.payment.method", string="Método")
    payment_amount = fields.Monetary(string="Importe")
    payment_line_ids = fields.One2many("pos.payment", related="order_id.payment_ids", readonly=False)

    @api.depends('amount_total', 'amount_paid', 'amount_tendered', 'payment_type')
    def _compute_payment_amounts(self):
        for wizard in self:
            due = wizard.amount_total - wizard.amount_paid
            wizard.amount_due = due
            if wizard.payment_type == 'cash':
                # Si diff < 0 significa que se entregó de más (cambio)
                diff = due - wizard.amount_tendered
                wizard.amount_change = diff
                wizard.amount_change_abs = abs(diff) if diff < 0 else 0.0
            else:
                wizard.amount_change = 0.0
                wizard.amount_change_abs = 0.0

    @api.onchange('operation_type', 'payment_type', 'amount_due')
    def _onchange_selections(self):
        if self.payment_type == 'cash' and not self.amount_tendered:
            self.amount_tendered = self.amount_due

        if self.payment_type == 'combined' and not self.payment_amount:
            self.payment_amount = self.amount_due

        if self.operation_type == 'ticket':
            self.document_type = 'factura_simplified'
        elif self.operation_type == 'invoice':
            self.document_type = 'factura_a4'

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
                'is_l100n_es_simplified_invoice': False,
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
        policy = self.order_id._get_conventional_credit_policy_data()
        if policy["needs_limit_override"]:
            raise UserError(_("El cliente ha superado su límite de riesgo. No se puede confirmar el pedido."))
        # El albarán también es directo, no pasa por pagos
        # Forzamos que salte a un nuevo pedido sin mostrar advertencia de falta de pago
        return self.order_id.with_context(skip_payment_warning=True).action_pay_account()

    def action_deposito(self):
        self.ensure_one()
        # El depósito es directo, usa la lógica del módulo original
        # Forzamos que salte a un nuevo pedido sin mostrar advertencia de falta de pago
        return self.order_id.with_context(skip_payment_warning=True).action_pay_deposit()

    def action_credito(self):
        return self.action_albaran()

    def confirm_payment_wizard_credit(self):
        """Metodo llamado tras aprobar un override de credito"""
        return self.action_albaran()

    def action_confirm(self):
        self.ensure_one()
        _logger.info("Confirmando pago en wizard. Tipo operacion: %s", self.operation_type)

        if self.operation_type == 'delivery':
            policy = self.order_id._get_conventional_credit_policy_data(allow_limit_override=self.env.context.get("allow_limit_override"))
            _logger.info("Política de crédito: %s", policy)
            if policy["needs_limit_override"]:
                raise UserError(_("El cliente ha superado su límite de riesgo. No se puede confirmar el pedido."))

        # Aplicamos la configuración del pedido según el tipo de operación
        if self.operation_type == 'ticket':
            self.order_id.write({
                'to_invoice': True,
                'is_a4_invoice': False,
                'is_l10n_es_simplified_invoice': True,
            })
        elif self.operation_type == 'invoice':
             self.order_id.write({
                'to_invoice': True,
                'is_a4_invoice': True,
                'is_l10n_es_simplified_invoice': False,
            })

        # Despachamos según la operación
        if self.operation_type in ['ticket', 'invoice']:
            if self.payment_type == 'cash':
                if not self.cash_method_id:
                    raise UserError(_("No se encontró método de pago en efectivo."))

                wizard = self.env['pos.make.payment.wizard'].with_context(
                    active_id=self.order_id.id,
                    cash_only=True,
                    cash_quick_mode=True
                ).create({
                    'order_id': self.order_id.id,
                    'payment_method_id': self.cash_method_id.id,
                    'amount_tendered': self.amount_tendered,
                })
                return wizard.action_validate()

            elif self.payment_type == 'card':
                return self.action_pago_tarjeta()

            elif self.payment_type == 'combined':
                # Si es combinado, ya hemos ido añadiendo pagos, ahora validamos
                if float_compare(self.amount_due, 0, precision_rounding=self.currency_id.rounding or 0.01) > 0:
                    raise UserError(_("El importe pagado es insuficiente."))

                # Usamos el wizard de pago estándar para finalizar el proceso (facturación, impresión, etc.)
                # con importe 0 ya que ya está pagado
                wizard = self.env['pos.make.payment.wizard'].with_context(
                    active_id=self.order_id.id,
                ).create({
                    'order_id': self.order_id.id,
                    'amount_tendered': 0,
                })
                return wizard.action_validate()

        elif self.operation_type == 'delivery':
            return self.action_albaran()

        elif self.operation_type == 'deposit':
            return self.action_deposito()


    def action_add_payment(self):
        self.ensure_one()
        if not self.selected_payment_method_id:
            raise UserError(_("Debe seleccionar un método de pago."))
        if float_is_zero(self.payment_amount, precision_rounding=self.currency_id.rounding or 0.01):
            raise UserError(_("El importe debe ser distinto de cero."))

        self.order_id.add_payment({
            'pos_order_id': self.order_id.id,
            'amount': self.payment_amount,
            'payment_method_id': self.selected_payment_method_id.id,
        })
        self.payment_amount = self.amount_due
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_delete_payment(self):
        # Este método ya no es accesible desde el tree si no está en el modelo pos.payment
        payment_id = self.env.context.get('payment_id')
        if payment_id:
            payment = self.env['pos.payment'].browse(payment_id)
            if payment.pos_order_id == self.order_id:
                payment.unlink()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def get_payment_methods(self):
        self.ensure_one()
        return [{
            'id': method.id,
            'name': method.name
        } for method in self.payment_method_ids]

class PosPayment(models.Model):
    _inherit = "pos.payment"

    def action_delete_payment_from_wizard(self):
        self.ensure_one()
        self.unlink()
