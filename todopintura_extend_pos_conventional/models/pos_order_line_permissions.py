from odoo import models
from odoo.exceptions import AccessError
from odoo.tools.translate import _


class PosOrderLinePermissions(models.Model):
    _inherit = 'pos.order.line'

    def write(self, vals):
        # Campos de precio que queremos proteger
        protected_fields = {'price_unit', 'discount'}
        if any(f in vals for f in protected_fields):
            # Si el usuario no tiene permitido editar precios, denegar
            if not getattr(self.env.user, 'pos_can_edit_price', False):
                raise AccessError(_('No tiene permisos para cambiar precios en TPV.'))
        return super(PosOrderLinePermissions, self).write(vals)

    @classmethod
    def _map_vals_list_has_protected(cls, vals_list):
        protected_fields = {'price_unit', 'discount'}
        for vals in vals_list:
            if any(f in vals for f in protected_fields):
                return True
        return False

    def create(self, vals_list):
        # Si se intenta crear líneas con precio distinto y el usuario no tiene permiso, denegar
        if self._map_vals_list_has_protected(vals_list):
            if not getattr(self.env.user, 'pos_can_edit_price', False):
                raise AccessError(_('No tiene permisos para crear líneas con precio modificado en TPV.'))
        return super(PosOrderLinePermissions, self).create(vals_list)

