# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class PosConventionalCreditCashierWarningWizard(models.TransientModel):
    _name = "pos.conventional.credit.cashier.warning.wizard"
    _description = "Confirmación de cobro cuando el cliente tiene crédito"

    order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Pedido POS",
        required=True,
        ondelete="cascade",
    )
    payment_method_id = fields.Many2one(
        comodel_name="pos.payment.method",
        string="Método de pago seleccionado",
    )
    payment_wizard_id = fields.Many2one(
        comodel_name="pos.make.payment.wizard",
        string="Wizard de pago origen",
        ondelete="cascade",
    )
    resume_action = fields.Selection(
        selection=[
            ("partner_selected", "Cliente seleccionado"),
            ("order_pay_cash", "Abrir cobro en efectivo"),
            ("order_pay_with_method", "Cobro rápido con método"),
            ("payment_wizard_add", "Añadir pago en popup"),
            ("payment_wizard_validate", "Validar popup de pago"),
        ],
        string="Acción a continuar",
        required=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="order_id.partner_id",
        string="Cliente",
        readonly=True,
    )
    revert_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente previo a restaurar",
        readonly=True,
    )
    warning_message = fields.Text(
        string="Aviso",
        required=True,
        readonly=True,
    )

    def action_continue(self):
        self.ensure_one()
        if not self.order_id:
            raise UserError(_("El pedido ya no está disponible."))

        if self.resume_action == "partner_selected":
            return {"type": "ir.actions.act_window_close"}

        if self.resume_action == "order_pay_cash":
            return self.order_id.with_context(
                skip_credit_cashier_warning=True,
            ).action_pay_cash()

        if self.resume_action == "order_pay_with_method":
            if not self.payment_method_id:
                raise UserError(_("No se ha indicado el método de pago a continuar."))
            return self.order_id.with_context(
                skip_credit_cashier_warning=True,
            ).action_pos_convention_pay_with_method(self.payment_method_id.id)

        if self.resume_action == "payment_wizard_add":
            if not self.payment_wizard_id:
                raise UserError(_("El popup de pago original ya no está disponible."))
            return self.payment_wizard_id.with_context(
                skip_credit_cashier_warning=True,
            ).action_add_payment()

        if self.resume_action == "payment_wizard_validate":
            if not self.payment_wizard_id:
                raise UserError(_("El popup de pago original ya no está disponible."))
            return self.payment_wizard_id.with_context(
                skip_credit_cashier_warning=True,
            ).action_validate()

        raise UserError(_("No se reconoce la acción a continuar."))

    def action_cancel(self):
        self.ensure_one()
        if self.resume_action == "partner_selected" and self.order_id:
            self.order_id.with_context(
                skip_completeness_check=True,
                skip_credit_cashier_warning=True,
            ).write({
                "partner_id": self.revert_partner_id.id or False,
            })
            return {"type": "ir.actions.client", "tag": "reload"}

        return {"type": "ir.actions.act_window_close"}

