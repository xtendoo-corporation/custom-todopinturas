# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosPayment(models.Model):
    _inherit = "pos.payment"

    def action_delete_payment_from_wizard(self):
        self.ensure_one()
        self.unlink()

class PosDepositPaymentWizardPaymentLine(models.TransientModel):
    _inherit = "pos.deposit.payment.wizard.payment.line"

    def action_delete_payment_from_wizard(self):
        self.ensure_one()
        self.unlink()

class PosPaymentSelectionWizard(models.TransientModel):
    _name = "pos.payment.selection.wizard"
    _description = "Selección de tipo de pago POS"

    order_id = fields.Many2one("pos.order", string="Pedido", required=False)
    deposit_wizard_id = fields.Many2one("pos.deposit.payment.wizard", string="Asistente de Depósitos", required=False)

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

    operation_type_deposit = fields.Selection([
        ('ticket', 'Factura simplificada'),
        ('invoice', 'Factura A4'),
    ], string="¿Qué desea hacer (Depósitos)?", default='ticket')

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

    partner_id = fields.Many2one("res.partner", compute="_compute_basic_fields", store=True, readonly=False)
    config_id = fields.Many2one("pos.config", compute="_compute_basic_fields", store=True, readonly=False)
    payment_method_ids = fields.Many2many("pos.payment.method", compute="_compute_basic_fields", store=True, readonly=False)
    show_deposit_button = fields.Boolean(compute="_compute_basic_fields", store=True)
    partner_deposit_enabled = fields.Boolean(compute="_compute_basic_fields", store=True)
    partner_deposit_available = fields.Boolean(compute="_compute_basic_fields", store=True)
    partner_deposit_warning_message = fields.Text(compute="_compute_basic_fields", store=True)
    partner_credit_available = fields.Boolean(compute="_compute_basic_fields", store=True)
    partner_credit_limit_exceeded = fields.Boolean(compute="_compute_credit_status")
    # Guardamos el estado de crédito en el momento de apertura del wizard
    partner_credit_available_at_open = fields.Boolean(string="Partner credit available at open", default=False, copy=False)

    # Campos de detalle de crédito para avisos
    partner_credit_limit = fields.Monetary(compute="_compute_basic_fields", store=True)
    partner_current_due = fields.Monetary(compute="_compute_basic_fields", store=True)
    partner_total_due_after = fields.Monetary(compute="_compute_basic_fields", store=True)

    @api.depends('order_id', 'deposit_wizard_id')
    def _compute_basic_fields(self):
        for wizard in self:
            if wizard.order_id:
                order = wizard.order_id
                wizard.partner_id = order.partner_id
                wizard.config_id = order.config_id
                wizard.payment_method_ids = order.config_id.payment_method_ids
                wizard.show_deposit_button = order.show_deposit_button
                wizard.partner_deposit_enabled = order.partner_deposit_enabled
                wizard.partner_deposit_available = order.partner_deposit_available
                wizard.partner_deposit_warning_message = order.partner_deposit_warning_message
                wizard.partner_credit_available = order.partner_credit_available
                wizard.partner_credit_limit = order.partner_credit_limit_amount
                wizard.partner_current_due = order.partner_current_total_due
                wizard.partner_total_due_after = order.partner_total_due_after_order
                # Inicializamos el flag solo la primera vez que se calcula para este wizard transient
                if not wizard.partner_credit_available_at_open:
                    # Guardamos el estado actual del crédito del partner al abrir el wizard
                    wizard.partner_credit_available_at_open = bool(order.partner_credit_available)
            elif wizard.deposit_wizard_id:
                dep_wiz = wizard.deposit_wizard_id
                wizard.partner_id = dep_wiz.partner_id
                wizard.config_id = dep_wiz.config_id
                wizard.payment_method_ids = dep_wiz.config_id.payment_method_ids
                wizard.show_deposit_button = False
                wizard.partner_deposit_enabled = False
                wizard.partner_deposit_available = False
                wizard.partner_deposit_warning_message = False
                wizard.partner_credit_available = False
                wizard.partner_credit_limit = 0.0
                wizard.partner_current_due = 0.0
                wizard.partner_total_due_after = 0.0

    @api.model
    def create(self, vals):
        # Aseguramos que al crear el wizard almacenamos el estado de crédito del partner
        wiz = super(PosPaymentSelectionWizard, self).create(vals)
        try:
            if wiz.order_id:
                wiz.partner_credit_available_at_open = bool(wiz.order_id.partner_credit_available)
        except Exception:
            # No hacemos nada si por alguna razón no está disponible
            pass
        return wiz

    @api.depends('order_id', 'operation_type')
    def _compute_credit_status(self):
        for wizard in self:
            if wizard.operation_type == 'delivery':
                policy = wizard.order_id._get_conventional_credit_policy_data()
                wizard.partner_credit_limit_exceeded = policy.get('limit_exceeded', False)
            else:
                wizard.partner_credit_limit_exceeded = False

    # Campos de importes para la vista unificada
    amount_total = fields.Monetary(compute="_compute_amounts", readonly=False)
    currency_id = fields.Many2one("res.currency", compute="_compute_amounts", readonly=False)
    currency_symbol = fields.Char(related="currency_id.symbol")
    amount_paid = fields.Monetary(compute="_compute_amounts", readonly=False)
    amount_due = fields.Monetary(compute="_compute_payment_amounts")
    amount_tendered = fields.Monetary(string="Importe Entregado")
    amount_change = fields.Monetary(string="Diferencia", compute="_compute_payment_amounts")
    amount_change_abs = fields.Monetary(string="Cambio", compute="_compute_payment_amounts")

    @api.depends('amount_total', 'amount_paid', 'amount_tendered')
    def _compute_payment_amounts(self):
        for wizard in self:
            wizard.amount_due = wizard.amount_total - wizard.amount_paid
            wizard.amount_change = wizard.amount_tendered - wizard.amount_due
            wizard.amount_change_abs = wizard.amount_change if wizard.amount_change > 0 else 0.0

    # Campos para Gestión de Pagos Combinados en la misma ventana
    selected_payment_method_id = fields.Many2one("pos.payment.method", string="Método")
    payment_amount = fields.Monetary(string="Importe")
    payment_line_ids = fields.Many2many("pos.payment", string="Pagos", compute="_compute_payment_lines")
    deposit_payment_line_ids = fields.Many2many("pos.deposit.payment.wizard.payment.line", string="Pagos Depósitos", compute="_compute_deposit_payment_lines")

    @api.depends('order_id', 'order_id.payment_ids')
    def _compute_payment_lines(self):
        for wizard in self:
            wizard.payment_line_ids = wizard.order_id.payment_ids if wizard.order_id else self.env['pos.payment']

    @api.depends('deposit_wizard_id', 'deposit_wizard_id.payment_line_ids')
    def _compute_deposit_payment_lines(self):
        for wizard in self:
            wizard.deposit_payment_line_ids = wizard.deposit_wizard_id.payment_line_ids if wizard.deposit_wizard_id else self.env['pos.deposit.payment.wizard.payment.line']

    def _inverse_payment_lines(self):
        pass

    @api.onchange('operation_type_deposit')
    def _onchange_operation_type_deposit(self):
        if self.operation_type_deposit:
            self.operation_type = self.operation_type_deposit

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
        if not self.order_id:
             # Para depósitos no abrimos el popup de pago estándar de POS
             return False
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

        if self.deposit_wizard_id:
            # Caso depósito: registramos el pago en el wizard de depósito y confirmamos
            method = self.env['pos.payment.method'].browse(payment_method_id)
            self.deposit_wizard_id.payment_line_ids.unlink()
            self.env['pos.deposit.payment.wizard.payment.line'].create({
                'wizard_id': self.deposit_wizard_id.id,
                'payment_method_id': method.id,
                'amount': self.amount_total,
            })
            # Forzamos la factura según la selección del wizard
            # (ticket/invoice ya mapeados a self.document_type)
            return self.action_confirm()

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
        policy = self.order_id._get_conventional_credit_policy_data()
        if policy["needs_limit_override"]:
            raise UserError(_("El cliente ha superado su límite de riesgo. No se puede confirmar el pedido."))
        # El albarán también es directo, no pasa por pagos
        # Forzamos que salte a un nuevo pedido sin mostrar advertencia de falta de pago
        # Aseguramos que además se suprima la advertencia de crédito en el flujo cliente
        return self.order_id.with_context(skip_payment_warning=True, skip_credit_cashier_warning=True).action_pay_account()

    def action_deposito(self):
        self.ensure_one()
        # El depósito es directo, usa la lógica del módulo original
        # Forzamos que salte a un nuevo pedido sin mostrar advertencia de falta de pago
        # Incluimos también la clave de contexto de skip_credit_cashier_warning por coherencia
        return self.order_id.with_context(skip_payment_warning=True, skip_credit_cashier_warning=True).action_pay_deposit()

    def action_credito(self):
        return self.action_albaran()

    def confirm_payment_wizard_credit(self):
        """Metodo llamado tras aprobar un override de credito"""
        return self.action_albaran()

    def action_confirm(self):
        self.ensure_one()
        _logger.info("Confirmando pago en wizard. Tipo operacion: %s", self.operation_type)

        if self.deposit_wizard_id:
            # Lógica para liquidación de depósitos
            # 1. Validamos que el importe esté cubierto (ya validado en is_payment_ready si fuera combined,
            # pero aquí es más directo para ticket/invoice)

            # Registramos los pagos en el wizard de depósito si es pago simple (cash/card)
            if self.payment_type in ['cash', 'card']:
                method_id = self.cash_method_id.id if self.payment_type == 'cash' else self.card_method_id.id
                if not method_id:
                     raise UserError(_("No se ha configurado el método de pago seleccionado."))

                self.deposit_wizard_id.payment_line_ids.unlink()
                self.env['pos.deposit.payment.wizard.payment.line'].create({
                    'wizard_id': self.deposit_wizard_id.id,
                    'payment_method_id': method_id,
                    'amount': self.amount_total,
                })

            # Creamos la factura a través del wizard de depósitos
            selected_orders = self.deposit_wizard_id._validate_selected_orders()
            # No llamamos a self.deposit_wizard_id.action_confirm() porque ya imprime,
            # queremos controlar la impresión según el tipo de documento.

            # Aplicamos la configuración del pedido según el tipo de operación ANTES de crear la factura
            if self.operation_type == 'ticket':
                selected_orders.write({
                    'is_l10n_es_simplified_invoice': True,
                    'is_a4_invoice': False,
                })
            else:
                selected_orders.write({
                    'is_l10n_es_simplified_invoice': False,
                    'is_a4_invoice': True,
                })

            invoice = selected_orders._create_conventional_deposit_invoice(
                invoice_partner=self.partner_id,
            )

            self.deposit_wizard_id._register_invoice_payments(invoice)
            invoice.invalidate_recordset(["payment_state", "amount_residual"])

            # Devolvemos la acción de impresión adecuada
            if self.operation_type == 'ticket':
                return self.deposit_wizard_id._build_print_simplified_invoice_action(invoice)
            else:
                # Para Factura A4, usamos el reporte estándar del wizard original modificado o el de account
                return self.deposit_wizard_id._build_invoice_action(invoice)

        if self.operation_type == 'delivery':
            policy = self.order_id._get_conventional_credit_policy_data(allow_limit_override=self.env.context.get("allow_limit_override"))
            _logger.info("Política de crédito: %s", policy)
            if policy["needs_limit_override"]:
                raise UserError(_("El cliente ha superado su límite de riesgo. No se puede confirmar el pedido."))

            # Determinar si imprimir albarán estándar o valorado según la config del cliente
            is_valued = (
                self.partner_id.delivery_report_print_type == 'valued' or
                (hasattr(self.partner_id, 'valued_picking') and self.partner_id.valued_picking)
            )
            # No forzamos skip_conventional_picking_print: delegamos en action_pay_account
            # para que devuelva la acción cliente de impresión con next_action incluido.
            context = dict(self.env.context)
            if is_valued:
                context['force_valued_picking'] = True
            # cuando venimos desde el wizard queremos suprimir el warning de crédito
            context['skip_credit_cashier_warning'] = True

            # Devolver la acción producida por action_pay_account, que imprimirá y
            # luego disparará la acción de nuevo pedido (pos_conventional_new_order).
            return self.order_id.with_context(**context).action_pay_account()

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

        if self.deposit_wizard_id:
            self.env['pos.deposit.payment.wizard.payment.line'].create({
                'wizard_id': self.deposit_wizard_id.id,
                'amount': self.payment_amount,
                'payment_method_id': self.selected_payment_method_id.id,
            })
            # Sincronizamos amount_paid desde el wizard de depósito
            self._compute_amounts()
        else:
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

    # Necesitamos que amount_paid se sincronice para depósitos también
    @api.depends('order_id', 'deposit_wizard_id', 'order_id.amount_paid', 'deposit_wizard_id.amount_paid_total')
    def _compute_amounts(self):
        for wizard in self:
            if wizard.order_id:
                wizard.amount_total = wizard.order_id.amount_total
                wizard.amount_paid = wizard.order_id.amount_paid
                wizard.currency_id = wizard.order_id.currency_id
            elif wizard.deposit_wizard_id:
                wizard.amount_total = wizard.deposit_wizard_id.amount_total
                wizard.amount_paid = wizard.deposit_wizard_id.amount_paid_total
                wizard.currency_id = wizard.deposit_wizard_id.currency_id

    def action_delete_payment(self):
        # Este método ya no es accesible desde el tree si no está en el modelo pos.payment
        payment_id = self.env.context.get('payment_id')
        dep_payment_id = self.env.context.get('dep_payment_id')
        if payment_id:
            payment = self.env['pos.payment'].browse(payment_id)
            if payment.exists() and payment.pos_order_id == self.order_id:
                payment.unlink()
        elif dep_payment_id:
            payment = self.env['pos.deposit.payment.wizard.payment.line'].browse(dep_payment_id)
            if payment.exists() and payment.wizard_id == self.deposit_wizard_id:
                payment.unlink()

        # Después de borrar, actualizamos importes
        self._compute_amounts()
        self.payment_amount = self.amount_due

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
