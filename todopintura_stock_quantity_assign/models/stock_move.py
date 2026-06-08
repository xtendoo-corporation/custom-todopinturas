# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribe el método create para evitar el llenado automático
        de cantidades en movimientos de stock.
        """
        for vals in vals_list:
            # Establecemos quantity a 0 para que el usuario lo rellene manualmente
            if 'quantity' not in vals:
                vals['quantity'] = 0.0

        return super().create(vals_list)

    def _action_confirm(self, merge=True, merge_into=False, **kwargs):
        """
        Sobrescribe _action_confirm para evitar que se rellenen
        automáticamente las cantidades al confirmar el movimiento.
        """
        res = super()._action_confirm(merge=merge, merge_into=merge_into, **kwargs)

        # 🔥 SOLUCIÓN: Filtramos self con .exists() para eliminar los registros
        # que el super() haya podido borrar/fusionar en la base de datos.
        self.exists().write({'quantity': 0.0})

        return res

    def _action_assign(self):
        """
        Sobrescribe _action_assign para evitar que se rellenen
        automáticamente las cantidades al asignar el movimiento.
        """
        res = super()._action_assign()

        # 🔥 SOLUCIÓN: Al asignar, Odoo puede desvincular o alterar
        # líneas en caliente, por lo que purgamos los IDs muertos de la caché.
        self.with_context(prefetch_fields=False).exists().write({'quantity': 0.0})

        return res
