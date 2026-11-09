# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command, api, models, tools

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
        own_groups = (
            self.env["res.groups"]
            .browse(user._get_group_ids())
            .filtered(
                lambda g: g.get_external_id().get(g.id, "").startswith(f"{MODULE}.")
            )
        )
        allowed_menus = (
            self.sudo()
            .with_context(active_test=False)
            .search([("group_ids", "in", own_groups.ids)])
        )
        allowed = set(allowed_menus.ids)
        for menu in allowed_menus:
            allowed.update(int(i) for i in menu.parent_path.split("/")[:-1])
        reachable = visible & allowed
        menus = self.sudo().browse(reachable)
        return frozenset(
            menu.id
            for menu in menus
            if all(int(i) in reachable for i in menu.parent_path.split("/")[:-1])
        )

    @api.model
    def _split_shared_actions(self):
        """Give every Todopintura menu its own window action.

        The web client picks the app to show from the action of the URL. When
        several menus (of other Todopintura apps or of the standard apps) share
        one action, a reload or a link can open the wrong app. Each menu of the
        module therefore gets a dedicated copy of its action (external id
        ``action_<menu id>``), kept in sync with the original on every update.
        """
        data = self.env["ir.model.data"].sudo()
        links = data.search([("module", "=", MODULE), ("model", "=", "ir.ui.menu")])
        for link in links:
            menu = self.sudo().browse(link.res_id).exists()
            original = menu.action
            if not original or original._name != "ir.actions.act_window":
                continue
            xml_name = f"action_{link.name}"
            own = self.env.ref(f"{MODULE}.{xml_name}", raise_if_not_found=False)
            if own:
                # Otherwise the end of the module update removes it as obsolete data.
                self.pool.loaded_xmlids.add(f"{MODULE}.{xml_name}")
            if own and original == own:
                continue  # already split and not reset by the menu data
            if own:
                own.write(self._split_action_values(original))
                own.view_ids.unlink()
            else:
                own = original.copy({"path": False, "binding_model_id": False})
                data._update_xmlids(
                    [{"xml_id": f"{MODULE}.{xml_name}", "record": own}]
                )
            own.write(
                {"view_ids": [Command.create(v) for v in self._split_view_values(original)]}
            )
            menu.action = f"ir.actions.act_window,{own.id}"

    @api.model
    def _split_action_values(self, action):
        values = {
            name: action[name]
            for name in (
                "res_model",
                "domain",
                "context",
                "view_mode",
                "mobile_view_mode",
                "target",
                "limit",
                "filter",
                "cache",
            )
        }
        values["view_id"] = action.view_id.id
        values["search_view_id"] = action.search_view_id.id
        values["group_ids"] = [Command.set(action.group_ids.ids)]
        return values

    @api.model
    def _split_view_values(self, action):
        return [
            {"sequence": view.sequence, "view_mode": view.view_mode, "view_id": view.view_id.id}
            for view in action.view_ids
        ]
