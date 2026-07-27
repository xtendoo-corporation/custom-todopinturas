from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    main_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Almacén principal',
        help='Almacén principal asociado al usuario',
    )

    pos_can_edit_price = fields.Boolean(
        string='Puede modificar precios en TPV',
        default=False,
        help='Permite al usuario cambiar manualmente el precio de líneas en el Punto de Venta',
    )

    @api.model
    def create(self, vals):
        user = super(ResUsers, self).create(vals)
        # ensure group membership matches flag on create
        if vals.get('pos_can_edit_price'):
            group = self.env.ref('todopintura_administration.group_pos_price_editor', raise_if_not_found=False)
            if group:
                # field is `group_ids` on res.users (not `groups_id`)
                user.sudo().write({'group_ids': [(4, group.id)]})
        return user

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        # if flag changed, sync group membership
        if 'pos_can_edit_price' in vals:
            group = self.env.ref('todopintura_administration.group_pos_price_editor', raise_if_not_found=False)
            if not group:
                return res
            for user in self:
                # synchronize the membership using the correct field name
                if user.pos_can_edit_price:
                    user.sudo().write({'group_ids': [(4, group.id)]})
                else:
                    user.sudo().write({'group_ids': [(3, group.id)]})
        return res

