# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class PosMakePaymentConventional(models.TransientModel):
    _inherit = "pos.make.payment"

    def _should_print_a4_invoice(self, order, params=None):
        self.ensure_one()
        params = params or {}
        if "is_a4_invoice" in params:
            return bool(params.get("is_a4_invoice"))
        return bool(getattr(order, "is_a4_invoice", False))

    def _convert_receipt_client_action_to_window(self, action, order):
        self.ensure_one()
        if not isinstance(action, dict) or action.get("tag") != "pos_conventional_print_receipt_client":
            return action

        params = dict(action.get("params") or {})
        params["is_a4_invoice"] = self._should_print_a4_invoice(order, params=params)
        move_id = params.get("move_id")
        if not move_id:
            return action

        report_xmlid = (
            "account.report_invoice_with_payments"
            if params["is_a4_invoice"]
            else "pos_conventional_receipt_custom.report_factura_simplificada_80mm"
        )
        params["url"] = f"/report/html/{report_xmlid}/{move_id}?download=false"
        params["report_autoprints"] = (
            report_xmlid == "pos_conventional_receipt_custom.report_factura_simplificada_80mm"
        )

        return {
            "type": "ir.actions.client",
            "tag": "pos_conventional_print_receipt_window",
            "params": params,
        }

    is_pay_later_payment = fields.Boolean(
        string="Pago a cuenta cliente",
        compute="_compute_credit_policy_display",
    )
    order_current_due = fields.Monetary(
        string="Deuda POS pendiente",
        compute="_compute_credit_policy_display",
        currency_field="config_currency_id",
    )
    order_credit_limit = fields.Monetary(
        string="Límite de riesgo",
        compute="_compute_credit_policy_display",
        currency_field="config_currency_id",
    )
    order_total_due_after_payment = fields.Monetary(
        string="Total tras la venta",
        compute="_compute_credit_policy_display",
        currency_field="config_currency_id",
    )
    order_current_credit_location_name = fields.Char(
        string="Ubicación de la caja",
        compute="_compute_credit_policy_display",
    )
    order_allowed_credit_location_names = fields.Char(
        string="Ubicaciones permitidas",
        compute="_compute_credit_policy_display",
    )
    order_pickup_people = fields.Text(
        string="Autorizados de recogida",
        compute="_compute_credit_policy_display",
    )
    order_requires_voucher = fields.Boolean(
        string="Necesita vale",
        compute="_compute_credit_policy_display",
    )
    order_voucher_reference = fields.Char(
        string="Código / documento del vale",
        compute="_compute_credit_policy_display",
    )
    order_credit_warning_message = fields.Text(
        string="Aviso de riesgo",
        compute="_compute_credit_policy_display",
    )
    order_credit_sale_enabled = fields.Boolean(
        string="Cliente habilitado para crédito",
        compute="_compute_credit_policy_display",
    )
    config_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_credit_policy_display",
    )

    def _get_active_order(self):
        return self.env["pos.order"].browse(self.env.context.get("active_id", False)).exists()

    @api.depends("amount", "payment_method_id")
    def _compute_credit_policy_display(self):
        for wizard in self:
            order = wizard._get_active_order()
            wizard.config_currency_id = order.currency_id if order else self.env.company.currency_id
            wizard.is_pay_later_payment = bool(wizard.payment_method_id and wizard.payment_method_id.type == "pay_later")
            wizard.order_current_due = 0.0
            wizard.order_credit_limit = 0.0
            wizard.order_total_due_after_payment = 0.0
            wizard.order_current_credit_location_name = False
            wizard.order_allowed_credit_location_names = False
            wizard.order_pickup_people = False
            wizard.order_requires_voucher = False
            wizard.order_voucher_reference = False
            wizard.order_credit_warning_message = False
            wizard.order_credit_sale_enabled = False
            if not order or not order.partner_id:
                continue

            policy = order._get_conventional_credit_policy_data(
                amount=wizard.amount,
                payment_method=wizard.payment_method_id,
            )
            wizard.order_current_due = policy["current_due"]
            wizard.order_credit_limit = policy["credit_limit"]
            wizard.order_total_due_after_payment = policy["total_after"]
            wizard.order_current_credit_location_name = policy["current_location_name"]
            wizard.order_allowed_credit_location_names = policy["allowed_location_names"]
            wizard.order_pickup_people = policy["pickup_people"]
            wizard.order_requires_voucher = policy["requires_voucher"]
            wizard.order_voucher_reference = policy["voucher_reference"]
            wizard.order_credit_warning_message = policy["warning_message"]
            wizard.order_credit_sale_enabled = policy["credit_sale_allowed"]

    def check(self, payment_method_id=None, force_print=False):
        self.ensure_one()
        if payment_method_id:
            self.payment_method_id = payment_method_id

        order = self._get_active_order()
        if order and self.payment_method_id and self.payment_method_id.type == "pay_later":
            if not order.partner_id:
                raise UserError("Debe seleccionar un cliente antes de registrar una venta a crédito.")

            policy = order._get_conventional_credit_policy_data(
                amount=self.amount,
                payment_method=self.payment_method_id,
                allow_limit_override=self.env.context.get("allow_conventional_credit_limit_override"),
            )
            if not policy["credit_sale_allowed"]:
                raise UserError(policy["error_message"])
            if not policy["location_allowed"]:
                raise UserError(policy["location_error"])
            if policy["needs_limit_override"]:
                return order._open_credit_limit_override_wizard(self, policy)
            return order._process_conventional_pay_later(
                payment_method=self.payment_method_id,
                amount=self.amount,
            )

        action = super().check(
            payment_method_id=payment_method_id,
            force_print=force_print,
        )
        if order:
            return self._convert_receipt_client_action_to_window(action, order)
        return action

