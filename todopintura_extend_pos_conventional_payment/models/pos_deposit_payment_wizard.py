# -*- coding: utf-8 -*-
from odoo import models, _

class PosDepositPaymentWizard(models.TransientModel):
    _inherit = "pos.deposit.payment.wizard"

    def action_go_to_payment_step(self):
        self.ensure_one()
        if not self.partner_id:
            from odoo.exceptions import UserError
            raise UserError(_("Debe seleccionar un cliente antes de continuar."))
        self._validate_selected_orders()

        # Limpiamos líneas de pago previas para que en el wizard unificado aparezca 0€ pagado al inicio
        self.payment_line_ids.unlink()

        # En lugar de ir al paso de pago interno, abrimos el wizard unificado
        view = self.env.ref("todopintura_extend_pos_conventional_payment.view_pos_payment_selection_wizard_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Seleccione tipo de pago"),
            "res_model": "pos.payment.selection.wizard",
            "view_mode": "form",
            "view_id": view.id,
            "target": "new",
            "context": {
                **self.env.context,
                "default_deposit_wizard_id": self.id,
                "default_operation_type": "ticket", # Por defecto Factura Simplificada
            },
        }
