# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class PosConventionalCreditOverrideWizard(models.TransientModel):
    _name = "pos.conventional.credit.override.wizard"
    _description = "Override de límite de riesgo en POS convencional"

    order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Pedido POS",
        required=True,
        readonly=True,
    )
    payment_wizard_id = fields.Many2one(
        comodel_name="pos.make.payment",
        string="Wizard de pago",
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="order_id.currency_id",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="order_id.partner_id",
        readonly=True,
    )
    current_due = fields.Monetary(string="Deuda POS pendiente", readonly=True, currency_field="currency_id")
    credit_limit = fields.Monetary(string="Límite de riesgo", readonly=True, currency_field="currency_id")
    payment_amount = fields.Monetary(string="Importe a crédito", readonly=True, currency_field="currency_id")
    total_after = fields.Monetary(string="Total tras la venta", readonly=True, currency_field="currency_id")
    current_location_name = fields.Char(string="Ubicación de la caja", readonly=True)
    allowed_location_names = fields.Char(string="Ubicaciones permitidas", readonly=True)
    pickup_people = fields.Text(string="Autorizados de recogida", readonly=True)
    requires_voucher = fields.Boolean(string="Necesita vale", readonly=True)
    voucher_reference = fields.Char(string="Código / documento del vale", readonly=True)
    warning_message = fields.Text(string="Advertencia", readonly=True)

    def action_confirm_override(self):
        self.ensure_one()
        if not self.payment_wizard_id.exists():
            raise UserError(_("La ventana de pago ya no está disponible. Vuelve a abrir el pago del pedido."))

        self.order_id.write({
            "credit_limit_override_approved": True,
            "credit_limit_override_user_id": self.env.user.id,
            "credit_limit_override_date": fields.Datetime.now(),
        })
        return self.payment_wizard_id.with_context(
            allow_conventional_credit_limit_override=True,
        ).check()



