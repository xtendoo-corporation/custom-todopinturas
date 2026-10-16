# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models, tools

MODULE = "todopintura_user_groups"


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @tools.ormcache("frozenset(self.env.user._get_group_ids())", "debug")
    def _visible_menu_ids(self, debug=False):
        """Los usuarios con grupos Todopintura solo ven los menus asignados a
        los permisos que tienen (mas sus menus padre)."""
        visible = super()._visible_menu_ids(debug=debug)
        user = self.env.user
        if user.has_group("base.group_system") or not user.has_group(
            f"{MODULE}.group_todopintura_restricted"
        ):
            return visible
        own_groups = self.env["res.groups"].browse(user._get_group_ids()).filtered(
            lambda g: g.get_external_id().get(g.id, "").startswith(f"{MODULE}.")
        )
        allowed_menus = self.sudo().with_context(active_test=False).search(
            [("group_ids", "in", own_groups.ids)]
        )
        allowed = set(allowed_menus.ids)
        for menu in allowed_menus:
            allowed.update(int(i) for i in menu.parent_path.split("/")[:-1])
        return visible & allowed
