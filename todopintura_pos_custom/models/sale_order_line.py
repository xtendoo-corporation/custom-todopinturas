# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_for_manual_price(self):
        """Método onchange adicional para mostrar advertencia en productos con precio manual"""
        # No llamamos al super() para evitar conflictos con otros métodos onchange

        # Verificamos si el producto tiene precio manual
        if self.product_id and self.product_id.manual_price:
            # Creamos el mensaje de advertencia
            warning_msg = _(
                'El producto "%s" está configurado para introducir '
                'el precio manualmente. Por favor, revise y ajuste '
                'el precio según sea necesario.'
            ) % (self.product_id.display_name)

            return {
                'warning': {
                    'title': _('Producto con precio manual'),
                    'message': warning_msg
                }
            }
        return None
