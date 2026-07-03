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
