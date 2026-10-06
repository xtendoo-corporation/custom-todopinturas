from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    main_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Almacén principal',
        help='Almacén principal asociado al usuario',
    )

    commercial_code = fields.Char(
        string='Código de comercial',
        copy=False,
        index=True,
        help='Código del comercial en el sistema anterior (columna COMERCIAL del Excel de clientes).',
    )

    pos_can_edit_price = fields.Boolean(
        string='Puede modificar precios en TPV',
        default=False,
        help='Permite al usuario cambiar manualmente el precio de líneas en el Punto de Venta',
    )

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        # ensure group membership matches flag on create
        group = self.env.ref('todopintura_administration.group_pos_price_editor', raise_if_not_found=False)
        if group:
            for user, vals in zip(users, vals_list):
                if vals.get('pos_can_edit_price'):
                    # field is `group_ids` on res.users (not `groups_id`)
                    user.sudo().write({'group_ids': [(4, group.id)]})
        return users

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

