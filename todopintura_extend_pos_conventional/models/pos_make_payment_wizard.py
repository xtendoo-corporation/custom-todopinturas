# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _


class PosMakePaymentWizard(models.TransientModel):
    _inherit = "pos.make.payment.wizard"

    def _should_print_a4_invoice(self, params=None):
        self.ensure_one()
        params = params or {}
        if "is_a4_invoice" in params:
            return bool(params.get("is_a4_invoice"))
        return bool(self.order_id.is_a4_invoice)

    def _convert_receipt_client_action_to_window(self, action):
        self.ensure_one()
        if not isinstance(action, dict) or action.get("tag") != "pos_conventional_print_receipt_client":
            return action

        params = dict(action.get("params") or {})
        params["is_a4_invoice"] = self._should_print_a4_invoice(params=params)
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

    show_credit_cashier_warning = fields.Boolean(
        string="Mostrar aviso de crédito al cajero",
        compute="_compute_credit_cashier_warning",
    )
    credit_cashier_warning_message = fields.Text(
        string="Mensaje de aviso de crédito",
        compute="_compute_credit_cashier_warning",
    )

    @api.depends(
        "order_id",
        "order_id.partner_id",
        "order_id.partner_credit_available",
        "order_id.partner_credit_cashier_warning",
        "payment_method_id",
    )
    def _compute_credit_cashier_warning(self):
        for wizard in self:
            order = wizard.order_id
            partner_has_credit = bool(order and order.partner_credit_available)
            uses_pay_later = bool(
                wizard.payment_method_id and wizard.payment_method_id.type == "pay_later"
            )
            wizard.show_credit_cashier_warning = bool(
                partner_has_credit and not uses_pay_later
            )
            wizard.credit_cashier_warning_message = False
            if wizard.show_credit_cashier_warning:
                wizard.credit_cashier_warning_message = (
                    order.partner_credit_cashier_warning
                    or _(
                        "ATENCIÓN: este cliente tiene crédito habilitado. "
                        "Si este pedido debe ir a cuenta, seleccione 'Pago Cuenta de cliente' "
                        "antes de continuar."
                    )
                )

    def action_add_payment(self):
        self.ensure_one()
        if self.payment_method_id and self.payment_method_id.type == "pay_later":
            _total, _paid, due = self._get_order_amounts(self.order_id)
            payment_wizard = self.env["pos.make.payment"].with_context(
                active_id=self.order_id.id,
            ).create({
                "amount": due,
                "payment_method_id": self.payment_method_id.id,
            })
            return payment_wizard.check()
        return super().action_add_payment()

    def _execute_validation(self, print_invoice=False):
        """
        Sobrescribe la validación para propagar el booleano 'is_a4_invoice'
        al pedido y a los parámetros del cliente de impresión.
        """
        order = self.order_id

        # Llamamos al original primero para que procese el pedido
        res = super()._execute_validation(print_invoice=print_invoice)

        # Si la acción es imprimir el ticket, inyectamos nuestro parámetro
        # Leemos el valor del pedido (que el cajero marcó en el form)
        if isinstance(res, dict) and res.get('tag') == 'pos_conventional_print_receipt_client':
            if 'params' not in res:
                res['params'] = {}
            res['params']['is_a4_invoice'] = self._should_print_a4_invoice()
        return self._convert_receipt_client_action_to_window(res)
