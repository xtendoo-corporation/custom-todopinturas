from odoo import api, models, tools


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @tools.ormcache(
        "frozenset(self.env.user._get_group_ids())",
        "debug",
        "self.env.user._tp_xtendoo_stock_barcode_visibility_cache_key()",
    )
    def _visible_menu_ids(self, debug=False):
        visible_ids = super()._visible_menu_ids(debug=debug)
        if self.env.user._tp_has_xtendoo_stock_barcode_access():
            return visible_ids

        xtendoo_barcode_menu = self.env.ref(
            "xtendoo_stock_barcode.menu_xtendoo_stock_barcode_root",
            raise_if_not_found=False,
        )
        if not xtendoo_barcode_menu:
            return visible_ids

        hidden_menu_ids = set(
            self.with_context({}).search([("id", "child_of", xtendoo_barcode_menu.id)]).ids
        )
        return frozenset(menu_id for menu_id in visible_ids if menu_id not in hidden_menu_ids)

