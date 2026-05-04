# -*- coding: utf-8 -*-

from odoo import models


class PosMakePaymentWizard(models.TransientModel):
    _inherit = "pos.make.payment.wizard"

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
            res['params']['is_a4_invoice'] = order.is_a4_invoice

        return res
