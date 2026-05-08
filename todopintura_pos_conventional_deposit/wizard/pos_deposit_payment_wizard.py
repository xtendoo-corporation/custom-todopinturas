# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.fields import Command
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero
from odoo.tools.translate import _


class PosDepositPaymentWizard(models.TransientModel):
    _name = "pos.deposit.payment.wizard"
    _description = "Asistente para pagar depósitos de POS convencional"

    def _is_cash_payment_method(self, payment_method):
        return bool(
            payment_method
            and (
                payment_method.is_cash_count
                or payment_method.journal_id.type == "cash"
                or payment_method.type == "cash"
            )
        )

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        domain="[('id', 'in', eligible_partner_ids)]",
    )
    session_id = fields.Many2one(
        "pos.session",
        string="Sesión TPV",
        required=True,
        readonly=True,
    )
    config_id = fields.Many2one(
        "pos.config",
        string="Caja",
        related="session_id.config_id",
        store=False,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="config_id.currency_id",
        store=False,
        readonly=True,
    )
    available_payment_method_ids = fields.Many2many(
        "pos.payment.method",
        compute="_compute_available_payment_method_ids",
    )
    eligible_partner_ids = fields.Many2many(
        "res.partner",
        compute="_compute_eligible_partner_ids",
    )
    deposit_order_line_ids = fields.One2many(
        "pos.deposit.payment.wizard.order.line",
        "wizard_id",
        string="Pedidos en depósito",
    )
    deposit_line_ids = fields.One2many(
        "pos.deposit.payment.wizard.line",
        "wizard_id",
        string="Líneas de pedido",
    )
    payment_line_ids = fields.One2many(
        "pos.deposit.payment.wizard.payment.line",
        "wizard_id",
        string="Líneas de pago",
    )
    step = fields.Selection(
        selection=[
            ("orders", "Pedidos"),
            ("lines", "Líneas de pedido"),
            ("payment", "Cobro"),
        ],
        string="Paso",
        default="orders",
        required=True,
    )
    selected_order_ids = fields.Many2many(
        "pos.order",
        compute="_compute_selected_order_ids",
    )
    deposit_order_count = fields.Integer(
        string="Pedidos encontrados",
        compute="_compute_selected_amounts",
    )
    selected_order_count = fields.Integer(
        string="Pedidos seleccionados",
        compute="_compute_selected_amounts",
    )
    amount_total = fields.Monetary(
        string="Total depósitos",
        compute="_compute_selected_amounts",
        currency_field="currency_id",
    )
    amount_paid_total = fields.Monetary(
        string="Importe indicado",
        compute="_compute_payment_amounts",
        currency_field="currency_id",
    )
    amount_due = fields.Monetary(
        string="Pendiente",
        compute="_compute_payment_amounts",
        currency_field="currency_id",
    )
    amount_change = fields.Monetary(
        string="Cambio a devolver",
        compute="_compute_payment_amounts",
        currency_field="currency_id",
    )
    non_cash_overpayment_amount = fields.Monetary(
        string="Exceso no permitido",
        compute="_compute_payment_amounts",
        currency_field="currency_id",
    )
    has_cash_payment = fields.Boolean(compute="_compute_payment_amounts")
    is_payment_ready = fields.Boolean(compute="_compute_payment_amounts")

    @api.depends("config_id")
    def _compute_available_payment_method_ids(self):
        for wizard in self:
            methods = wizard.config_id.payment_method_ids.filtered(
                lambda method: method.type != "pay_later"
            )
            wizard.available_payment_method_ids = methods

    @api.depends("session_id", "config_id")
    def _compute_eligible_partner_ids(self):
        for wizard in self:
            if not wizard.config_id:
                wizard.eligible_partner_ids = self.env["res.partner"]
                continue

            orders = self.env["pos.order"].search(
                [
                    ("config_id", "=", wizard.config_id.id),
                    ("state", "in", ("deposit", "deposit_partial")),
                    ("partner_id", "!=", False),
                ]
            )
            wizard.eligible_partner_ids = orders.mapped("partner_id.commercial_partner_id")

    @api.depends("deposit_order_line_ids.selected", "deposit_order_line_ids.order_id")
    def _compute_selected_order_ids(self):
        for wizard in self:
            wizard.selected_order_ids = wizard.deposit_order_line_ids.filtered("selected").mapped(
                "order_id"
            )

    @api.depends(
        "step",
        "deposit_order_line_ids",
        "deposit_order_line_ids.selected",
        "deposit_order_line_ids.order_id.lines",
        "deposit_order_line_ids.order_id.lines.is_deposit_paid",
        "deposit_line_ids",
        "deposit_line_ids.selected",
    )
    def _compute_selected_amounts(self):
        for wizard in self:
            wizard.deposit_order_count = len(wizard.deposit_order_line_ids)
            if wizard.step == "orders":
                selected_orders = wizard.deposit_order_line_ids.filtered("selected")
                wizard.selected_order_count = len(selected_orders)
                lines = selected_orders.mapped("order_id.lines").filtered(lambda l: not l.is_deposit_paid)
                wizard.amount_total = sum(lines.mapped("price_subtotal_incl"))
            else:
                selected_lines = wizard.deposit_line_ids.filtered("selected")
                wizard.selected_order_count = len(selected_lines.mapped("order_line_id.order_id"))
                wizard.amount_total = sum(selected_lines.mapped("price_subtotal_incl"))

    def _get_payment_breakdown(self):
        self.ensure_one()
        currency = self.currency_id or self.env.company.currency_id
        rounding = currency.rounding
        payment_lines = self.payment_line_ids.filtered(
            lambda line: line.payment_method_id and line.amount > 0
        )
        cash_lines = payment_lines.filtered("is_cash_payment")
        non_cash_lines = payment_lines - cash_lines

        total_non_cash = sum(non_cash_lines.mapped("amount"))
        total_cash_tendered = sum(cash_lines.mapped("amount"))
        total_tendered = total_non_cash + total_cash_tendered

        non_cash_overpayment = max(total_non_cash - self.amount_total, 0.0)
        remaining_after_non_cash = max(self.amount_total - min(total_non_cash, self.amount_total), 0.0)
        cash_applied = min(total_cash_tendered, remaining_after_non_cash)
        amount_change = max(total_cash_tendered - cash_applied, 0.0)
        amount_due = max(self.amount_total - min(total_non_cash, self.amount_total) - cash_applied, 0.0)

        remaining_to_register = self.amount_total
        register_lines = []
        for line in non_cash_lines:
            applied_amount = min(line.amount, remaining_to_register)
            if float_compare(applied_amount, 0.0, precision_rounding=rounding) > 0:
                register_lines.append((line, applied_amount))
                remaining_to_register -= applied_amount
        for line in cash_lines:
            applied_amount = min(line.amount, remaining_to_register)
            if float_compare(applied_amount, 0.0, precision_rounding=rounding) > 0:
                register_lines.append((line, applied_amount))
                remaining_to_register -= applied_amount

        return {
            "payment_lines": payment_lines,
            "total_tendered": total_tendered,
            "amount_due": amount_due,
            "amount_change": amount_change,
            "non_cash_overpayment": non_cash_overpayment,
            "has_cash_payment": bool(cash_lines),
            "register_lines": register_lines,
        }

    @api.depends("payment_line_ids.amount", "amount_total")
    def _compute_payment_amounts(self):
        for wizard in self:
            payment_breakdown = wizard._get_payment_breakdown()
            wizard.amount_paid_total = payment_breakdown["total_tendered"]
            wizard.amount_due = payment_breakdown["amount_due"]
            wizard.amount_change = payment_breakdown["amount_change"]
            wizard.non_cash_overpayment_amount = payment_breakdown["non_cash_overpayment"]
            wizard.has_cash_payment = payment_breakdown["has_cash_payment"]
            wizard.is_payment_ready = bool(
                wizard.selected_order_count
                and payment_breakdown["payment_lines"]
                and float_is_zero(
                    payment_breakdown["amount_due"],
                    precision_rounding=wizard.currency_id.rounding,
                )
                and float_is_zero(
                    payment_breakdown["non_cash_overpayment"],
                    precision_rounding=wizard.currency_id.rounding,
                )
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        session = self.env["pos.order"]._get_conventional_deposit_session_from_context()
        if session:
            res["session_id"] = session.id
        return res

    def _get_eligible_orders(self):
        self.ensure_one()
        if not (self.partner_id and self.config_id):
            return self.env["pos.order"]
        return self.env["pos.order"].search(
            [
                (
                    "partner_id.commercial_partner_id",
                    "=",
                    self.partner_id.commercial_partner_id.id,
                ),
                ("config_id", "=", self.config_id.id),
                ("state", "in", ("deposit", "deposit_partial")),
            ],
            order="date_order desc, id desc",
        )

    def _get_eligible_orders_for(self, partner=None, config=None):
        self.ensure_one()
        partner = partner or self.partner_id
        config = config or self.config_id
        if not (partner and config):
            return self.env["pos.order"]
        return self.env["pos.order"].search(
            [
                (
                    "partner_id.commercial_partner_id",
                    "=",
                    partner.commercial_partner_id.id,
                ),
                ("config_id", "=", config.id),
                ("state", "in", ("deposit", "deposit_partial")),
            ],
            order="date_order desc, id desc",
        )

    def _prepare_order_lines_commands(self, orders):
        return [
            Command.create(
                {
                    "order_id": order.id,
                    "selected": False,
                }
            )
            for order in orders
        ]

    def _get_default_payment_line_commands(self):
        self.ensure_one()
        payment_method = self.available_payment_method_ids.filtered(
            lambda method: self._is_cash_payment_method(method)
        )[:1] or self.available_payment_method_ids[:1]
        if not payment_method:
            return [Command.clear()]
        return [
            Command.clear(),
            Command.create(
                {
                    "payment_method_id": payment_method.id,
                    "amount": 0.0,
                }
            ),
        ]

    def _sync_single_payment_line_amount(self):
        self.ensure_one()
        if not self.payment_line_ids:
            return
        rounding = self.currency_id.rounding
        if len(self.payment_line_ids) == 1:
            self.payment_line_ids.amount = self.amount_total
            return
        if float_is_zero(self.amount_total, precision_rounding=rounding):
            for line in self.payment_line_ids:
                line.amount = 0.0

    def _reload_persisted_lines(self, partner=None):
        self.ensure_one()
        partner = partner or self.partner_id
        orders = self._get_eligible_orders_for(partner=partner, config=self.config_id)

        self.deposit_order_line_ids.unlink()
        self.payment_line_ids.unlink()

        if orders:
            self.env["pos.deposit.payment.wizard.order.line"].create(
                [
                    {
                        "wizard_id": self.id,
                        "order_id": order.id,
                        "selected": False,
                    }
                    for order in orders
                ]
            )

        payment_method = self.available_payment_method_ids.filtered(
            lambda method: self._is_cash_payment_method(method)
        )[:1] or self.available_payment_method_ids[:1]
        if payment_method:
            self.env["pos.deposit.payment.wizard.payment.line"].create(
                {
                    "wizard_id": self.id,
                    "payment_method_id": payment_method.id,
                    "amount": 0.0,
                }
            )

        self.invalidate_recordset(["deposit_order_line_ids", "payment_line_ids"])
        self._sync_single_payment_line_amount()

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for wizard in self:
            wizard.step = "orders"
            persisted_wizard = wizard._origin if wizard._origin and wizard._origin.id else wizard
            if persisted_wizard.id:
                persisted_wizard._reload_persisted_lines(partner=wizard.partner_id)
                wizard.deposit_order_line_ids = persisted_wizard.deposit_order_line_ids
                wizard.payment_line_ids = persisted_wizard.payment_line_ids
                continue

            orders = wizard._get_eligible_orders()
            wizard.deposit_order_line_ids = [Command.clear(), *wizard._prepare_order_lines_commands(orders)]
            wizard.payment_line_ids = wizard._get_default_payment_line_commands()
            wizard._sync_single_payment_line_amount()

    @api.onchange("deposit_order_line_ids", "deposit_order_line_ids.selected", "deposit_order_line_ids.order_id")
    def _onchange_deposit_order_line_ids(self):
        for wizard in self:
            wizard._sync_single_payment_line_amount()

    def _get_reopen_action(self):
        self.ensure_one()
        view = self.env.ref(
            "todopintura_pos_conventional_deposit.view_pos_deposit_payment_wizard_form"
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "view_id": view.id,
            "views": [(view.id, "form")],
            "target": "new",
            "context": {
                **self.env.context,
                "dialog_size": "xl",
            },
        }

    def _validate_selected_orders(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Debe seleccionar un cliente antes de continuar."))
        selected_orders = self.selected_order_ids.exists()
        if not selected_orders:
            raise UserError(_("Debe seleccionar al menos un pedido en depósito."))
        commercial_partner = self.partner_id.commercial_partner_id
        if any(
            order.partner_id.commercial_partner_id != commercial_partner
            for order in selected_orders
        ):
            raise UserError(
                _("Todos los pedidos seleccionados deben pertenecer al cliente indicado.")
            )
        if any(order.config_id != self.config_id for order in selected_orders):
            raise UserError(
                _("Todos los pedidos seleccionados deben pertenecer a la caja actual.")
            )
        return selected_orders

    def action_go_to_payment_step(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Debe seleccionar un cliente antes de continuar."))
        self._validate_selected_orders()
        self.step = "payment"
        self._sync_single_payment_line_amount()
        return self._get_reopen_action()

    def action_back_to_order_step(self):
        self.ensure_one()
        self.step = "orders"
        return self._get_reopen_action()

    def action_select_all_orders(self):
        self.ensure_one()
        for line in self.deposit_order_line_ids:
            line.selected = True
        self._sync_single_payment_line_amount()
        return self._get_reopen_action()

    def action_clear_selected_orders(self):
        self.ensure_one()
        for line in self.deposit_order_line_ids:
            line.selected = False
        self._sync_single_payment_line_amount()
        return self._get_reopen_action()

    def _register_invoice_payments(self, invoice):
        self.ensure_one()
        payment_breakdown = self._get_payment_breakdown()
        self._validate_payment_breakdown(payment_breakdown=payment_breakdown, currency=invoice.currency_id)
        created_payments = self.env["account.payment"]
        for line, payment_amount in payment_breakdown["register_lines"]:
            payment_register = self.env["account.payment.register"].with_context(
                active_model="account.move",
                active_ids=invoice.ids,
                force_payment_move=True,
            ).create(
                {
                    "amount": payment_amount,
                    "journal_id": line.payment_method_id.journal_id.id,
                    "payment_date": fields.Date.context_today(self),
                }
            )
            manual_payment_method_line = payment_register.available_payment_method_line_ids.filtered(
                lambda method_line: method_line.code == "manual"
            )[:1]
            if manual_payment_method_line:
                payment_register.payment_method_line_id = manual_payment_method_line
            payments = payment_register._create_payments()
            draft_payments = payments.filtered(lambda p: p.state == "draft")
            if draft_payments:
                draft_payments.action_post()
            created_payments |= payments

        created_payments.invalidate_recordset(["move_id", "destination_account_id"])
        payment_moves = created_payments.mapped("move_id")
        if payment_moves:
            payment_moves.invalidate_recordset(["line_ids"])
        invoice.invalidate_recordset(["line_ids", "payment_state", "amount_residual"])

        valid_account_types = self.env["account.payment"]._get_valid_payment_account_types()
        invoice_open_lines = invoice.line_ids.filtered(
            lambda move_line: move_line.parent_state == "posted"
            and move_line.account_type in valid_account_types
            and not move_line.reconciled
        )
        payment_open_lines = payment_moves.line_ids.filtered(
            lambda move_line: move_line.parent_state == "posted"
            and move_line.account_type in valid_account_types
            and not move_line.reconciled
        )
        common_accounts = invoice_open_lines.mapped("account_id") & payment_open_lines.mapped(
            "account_id"
        )
        for account in common_accounts:
            (invoice_open_lines | payment_open_lines).filtered(
                lambda move_line: move_line.account_id == account and not move_line.reconciled
            ).reconcile()

        invoice.invalidate_recordset(["payment_state", "amount_residual"])

    def _validate_payment_breakdown(self, payment_breakdown=None, currency=None):
        self.ensure_one()
        payment_breakdown = payment_breakdown or self._get_payment_breakdown()
        payment_lines = payment_breakdown["payment_lines"]
        if not payment_lines:
            raise UserError(_("Debe indicar al menos una línea de pago."))

        currency = currency or self.currency_id or self.env.company.currency_id
        if any(line.payment_method_id.type == "pay_later" for line in payment_lines):
            raise UserError(
                _("El método 'Cuenta de cliente' no puede utilizarse para liquidar depósitos.")
            )
        if (
            float_compare(
                payment_breakdown["non_cash_overpayment"],
                0.0,
                precision_rounding=currency.rounding,
            )
            > 0
        ):
            raise UserError(
                _(
                    "Los métodos de pago distintos de efectivo no pueden superar el total a cobrar."
                )
            )
        if (
            float_compare(
                payment_breakdown["amount_due"],
                0.0,
                precision_rounding=currency.rounding,
            )
            > 0
        ):
            raise UserError(
                _("Todavía falta importe por cobrar para completar la liquidación de depósitos.")
            )

    def _build_invoice_action(self, invoice):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": invoice.display_name,
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
            "context": {
                **self.env.context,
                "dialog_size": "extra-large",
            },
        }

    def _build_print_simplified_invoice_action(self, invoice):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "pos_conventional_print_receipt_window",
            "params": {
                "move_id": invoice.id,
                "url": (
                    "/report/html/"
                    "pos_conventional_receipt_custom.report_factura_simplificada_80mm/"
                    f"{invoice.id}?download=false"
                ),
                "report_autoprints": True,
                "clear_breadcrumbs": False,
                "next_action": self._build_invoice_action(invoice),
            },
        }

    def action_go_to_lines_step(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Debe seleccionar un cliente antes de continuar."))
        selected_orders = self._validate_selected_orders()

        # Populate deposit_line_ids with all lines from selected orders that are not paid yet
        lines_to_pay = selected_orders.mapped("lines").filtered(lambda l: not l.is_deposit_paid)
        self.deposit_line_ids = [Command.clear()]
        vals = []
        for line in lines_to_pay:
            vals.append((0, 0, {
                "order_line_id": line.id,
                "selected": True,
            }))
        self.write({
            "deposit_line_ids": vals,
            "step": "lines",
        })
        return self._get_reopen_action()

    def action_back_to_lines_step(self):
        self.ensure_one()
        self.step = "lines"
        return self._get_reopen_action()

    def action_select_all_lines(self):
        self.ensure_one()
        for line in self.deposit_line_ids:
            line.selected = True
        self._sync_single_payment_line_amount()
        return self._get_reopen_action()

    def action_clear_selected_lines(self):
        self.ensure_one()
        for line in self.deposit_line_ids:
            line.selected = False
        self._sync_single_payment_line_amount()
        return self._get_reopen_action()

    def action_confirm(self):
        self.ensure_one()
        selected_wizard_lines = self.deposit_line_ids.filtered("selected")
        if not selected_wizard_lines:
            raise UserError(_("Debe seleccionar al menos una línea de pedido para pagar."))
        selected_pos_lines = selected_wizard_lines.mapped("order_line_id")
        selected_orders = selected_pos_lines.mapped("order_id")
        self._validate_payment_breakdown()

        invoice = selected_orders._create_conventional_deposit_invoice(
            invoice_partner=self.partner_id,
            lines_to_invoice=selected_pos_lines.ids
        )
        self._register_invoice_payments(invoice)
        invoice.invalidate_recordset(["payment_state", "amount_residual"])
        return self._build_print_simplified_invoice_action(invoice)


class PosDepositPaymentWizardOrderLine(models.TransientModel):
    _name = "pos.deposit.payment.wizard.order.line"
    _description = "Línea de pedido en depósito a liquidar"
    _order = "date_order desc, id desc"

    wizard_id = fields.Many2one(
        "pos.deposit.payment.wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="Seleccionar")
    order_id = fields.Many2one(
        "pos.order",
        string="Pedido",
        required=True,
        ondelete="cascade",
        check_company=False,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="wizard_id.currency_id",
        store=False,
        readonly=True,
    )
    display_reference = fields.Char(
        string="Referencia",
        compute="_compute_display_reference",
        readonly=True,
    )
    date_order = fields.Datetime(related="order_id.date_order", string="Fecha", readonly=True)
    amount_total = fields.Monetary(
        related="order_id.amount_total",
        string="Importe",
        readonly=True,
        currency_field="currency_id",
    )
    picking_count = fields.Integer(related="order_id.picking_count", string="Pickings", readonly=True)

    @api.depends("order_id.name", "order_id.pos_reference", "order_id.tracking_number")
    def _compute_display_reference(self):
        for line in self:
            order = line.order_id
            line.display_reference = (
                order.pos_reference
                or order.tracking_number
                or (order.name if order.name and order.name != "/" else False)
                or _("Pedido %s") % order.id
            )


class PosDepositPaymentWizardPaymentLine(models.TransientModel):
    _name = "pos.deposit.payment.wizard.payment.line"
    _description = "Línea de pago para liquidar depósitos"

    wizard_id = fields.Many2one(
        "pos.deposit.payment.wizard",
        required=True,
        ondelete="cascade",
    )
    available_payment_method_ids = fields.Many2many(
        "pos.payment.method",
        related="wizard_id.available_payment_method_ids",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="wizard_id.currency_id",
        store=False,
        readonly=True,
    )
    payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Método de pago",
        required=True,
        domain="[('id', 'in', available_payment_method_ids)]",
    )
    is_cash_payment = fields.Boolean(
        string="Es efectivo",
        compute="_compute_is_cash_payment",
    )
    amount = fields.Monetary(
        string="Importe",
        required=True,
        currency_field="currency_id",
        default=0.0,
    )

    @api.depends("payment_method_id")
    def _compute_is_cash_payment(self):
        for line in self:
            line.is_cash_payment = line.wizard_id._is_cash_payment_method(line.payment_method_id)


class PosDepositPaymentWizardLine(models.TransientModel):
    _name = "pos.deposit.payment.wizard.line"
    _description = "Línea de depósito a liquidar individualmente"

    wizard_id = fields.Many2one(
        "pos.deposit.payment.wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="Seleccionar", default=True)
    order_line_id = fields.Many2one(
        "pos.order.line",
        string="Línea de pedido",
        required=True,
        ondelete="cascade",
    )
    order_id = fields.Many2one(
        "pos.order",
        related="order_line_id.order_id",
        string="Pedido",
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product",
        related="order_line_id.product_id",
        string="Producto",
        readonly=True,
    )
    qty = fields.Float(
        related="order_line_id.qty",
        string="Cantidad",
        readonly=True,
    )
    price_unit = fields.Float(
        related="order_line_id.price_unit",
        string="P.U.",
        readonly=True,
    )
    price_subtotal_incl = fields.Monetary(
        related="order_line_id.price_subtotal_incl",
        string="Subtotal",
        readonly=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="order_line_id.currency_id",
        store=False,
        readonly=True,
    )


