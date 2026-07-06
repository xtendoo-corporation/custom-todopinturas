# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_open_payment_selection_wizard(self):
        self.ensure_one()
        view = self.env.ref('todopintura_extend_pos_conventional_payment.view_pos_payment_selection_wizard_form')
        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.payment.selection.wizard",
            "name": _("Seleccione tipo de pago"),
            "view_mode": "form",
            "view_id": view.id,
            "target": "new",
            "context": {
                "default_order_id": self.id,
            },
        }

    def action_pay_account(self):
        """Sobrescribimos para asegurar que retorne la acción de nuevo pedido"""
        res = super(PosOrder, self).action_pay_account()
        # Si el resultado es abrir el formulario del pedido actual (lo que hace el original),
        # lo cambiamos por la acción de nuevo pedido.
        if isinstance(res, dict) and res.get('res_model') == 'pos.order' and res.get('res_id') == self.id:
            return self._get_post_validation_action()
        return res

    def action_pay_deposit(self):
        """Sobrescribimos para asegurar que retorne la acción de nuevo pedido tras enviar a depósito"""
        res = super(PosOrder, self).action_pay_deposit()
        if isinstance(res, dict) and res.get('res_model') == 'pos.order' and res.get('res_id') == self.id:
            return self._get_post_validation_action()
        return res
