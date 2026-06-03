# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribe el método create para evitar el llenado automático
        de cantidades en movimientos de stock relacionados con compras.
        """
        for vals in vals_list:
            # Si el movimiento está relacionado con una compra (purchase_line_id)
            # establecemos la cantidad a 0 para que no se rellene automáticamente
            if vals.get('purchase_line_id'):
                # Guardamos la cantidad original si existe
                original_quantity = vals.get('product_uom_qty', 0)
                
                # Establecemos quantity a 0 para que el usuario lo rellene manualmente
                if 'quantity' not in vals:
                    vals['quantity'] = 0.0
        
        return super().create(vals_list)

    def _action_confirm(self, merge=True, merge_into=False):
        """
        Sobrescribe _action_confirm para evitar que se rellenen
        automáticamente las cantidades al confirmar el movimiento.
        """
        res = super()._action_confirm(merge=merge, merge_into=merge_into)
        
        # Para movimientos relacionados con compras, establecemos quantity a 0
        purchase_moves = self.filtered(lambda m: m.purchase_line_id)
        if purchase_moves:
            purchase_moves.write({'quantity': 0.0})
        
        return res

    def _action_assign(self):
        """
        Sobrescribe _action_assign para evitar que se rellenen
        automáticamente las cantidades al asignar el movimiento.
        """
        res = super()._action_assign()
        
        # Para movimientos relacionados con compras, mantenemos quantity a 0
        purchase_moves = self.filtered(lambda m: m.purchase_line_id)
        if purchase_moves:
            purchase_moves.write({'quantity': 0.0})
        
        return res
