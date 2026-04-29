# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosMakePaymentWizard(models.TransientModel):
    _inherit = "pos.make.payment.wizard"

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
