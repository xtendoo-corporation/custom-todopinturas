# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.todopintura_user_groups import hooks

MODULE = "todopintura_user_groups"


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestAdoption(TransactionCase):
    """Hand-made records (no external id) are adopted instead of duplicated."""

    def _strip_xmlid(self, xml_id):
        record = self.env.ref(f"{MODULE}.{xml_id}")
        self.env["ir.model.data"].search(
            [("module", "=", MODULE), ("name", "=", xml_id)]
        ).unlink()
        return record

    def test_group_is_adopted_by_name(self):
        group = self._strip_xmlid("perm_va01")
        hooks.adopt_manual_records(self.env)
        self.assertEqual(self.env.ref(f"{MODULE}.perm_va01"), group)
        self.assertEqual(
            self.env["res.groups"].search_count([("name", "=", group.name)]), 1
        )

    def test_privilege_and_category_are_adopted(self):
        privilege = self._strip_xmlid("privilege_10_direccion")
        category = self._strip_xmlid("module_category_todopintura")
        hooks.adopt_manual_records(self.env)
        self.assertEqual(self.env.ref(f"{MODULE}.privilege_10_direccion"), privilege)
        self.assertEqual(
            self.env.ref(f"{MODULE}.module_category_todopintura"), category
        )

    def test_menu_is_adopted_by_path(self):
        menu = self._strip_xmlid("menu_vt_prices")
        hooks.adopt_manual_records(self.env)
        self.assertEqual(self.env.ref(f"{MODULE}.menu_vt_prices"), menu)

    def test_same_menu_name_under_other_root_is_not_confused(self):
        menu = self._strip_xmlid("menu_vc_prices")
        hooks.adopt_manual_records(self.env)
        self.assertEqual(self.env.ref(f"{MODULE}.menu_vc_prices"), menu)
        self.assertNotEqual(
            self.env.ref(f"{MODULE}.menu_vc_prices"),
            self.env.ref(f"{MODULE}.menu_vt_prices"),
        )

    def test_access_is_adopted_by_model_and_group(self):
        access = self._strip_xmlid("access_pos_order_va01")
        access.name = "nombre manual cualquiera"
        hooks.adopt_manual_records(self.env)
        self.assertEqual(self.env.ref(f"{MODULE}.access_pos_order_va01"), access)

    def test_pos_and_warehouse_are_adopted(self):
        config = self._strip_xmlid("pos_config_huelva")
        warehouse = self._strip_xmlid("warehouse_huelva")
        hooks.adopt_manual_records(self.env)
        self.assertEqual(self.env.ref(f"{MODULE}.pos_config_huelva"), config)
        self.assertEqual(self.env.ref(f"{MODULE}.warehouse_huelva"), warehouse)

    def test_warehouse_found_through_its_pos_even_if_renamed(self):
        warehouse = self._strip_xmlid("warehouse_ayamonte")
        warehouse.name = "Tienda de Ayamonte"
        hooks.adopt_manual_records(self.env)
        self.assertEqual(self.env.ref(f"{MODULE}.warehouse_ayamonte"), warehouse)

    def test_pricelist_is_adopted(self):
        pricelist = self._strip_xmlid("pricelist_outlet")
        hooks.adopt_manual_records(self.env)
        self.assertEqual(self.env.ref(f"{MODULE}.pricelist_outlet"), pricelist)

    def test_ambiguous_name_is_not_adopted(self):
        group = self._strip_xmlid("perm_va01")
        group.copy({"name": group.name})
        hooks.adopt_manual_records(self.env)
        self.assertFalse(self.env.ref(f"{MODULE}.perm_va01", raise_if_not_found=False))

    def test_stale_implied_group_is_removed(self):
        store = self.env.ref(f"{MODULE}.group_06_ventas_de_tiendas")
        stale = self.env.ref(f"{MODULE}.perm_va05")
        store.implied_ids = [Command.link(stale.id)]
        self.assertIn(stale, store.implied_ids)
        hooks.reset_declared_implied_groups(self.env)
        self.assertNotIn(stale, store.implied_ids)
        self.assertIn(self.env.ref(f"{MODULE}.perm_va01"), store.implied_ids)

    def test_reset_keeps_standard_groups_extended_by_the_module(self):
        hooks.reset_declared_implied_groups(self.env)
        self.assertIn(
            self.env.ref(f"{MODULE}.group_cost_viewer"),
            self.env.ref("base.group_system").implied_ids,
        )

    def test_user_loses_permissions_no_profile_implies_any_more(self):
        store = self.env.ref(f"{MODULE}.group_06_ventas_de_tiendas")
        stale = self.env.ref(f"{MODULE}.perm_va05")
        store.implied_ids = [Command.link(stale.id)]
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Stale",
                    "login": "stale_user",
                    "group_ids": [Command.set(store.ids)],
                }
            )
        )
        self.assertIn(stale, user.group_ids)
        hooks.reset_declared_implied_groups(self.env)
        self.assertNotIn(stale, user.group_ids)
        self.assertIn(self.env.ref(f"{MODULE}.perm_va01"), user.group_ids)

    def test_reset_is_idempotent_and_keeps_manual_users_untouched(self):
        manual = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Manual",
                    "login": "manual_user",
                    "group_ids": [Command.set(self.env.ref(f"{MODULE}.perm_va05").ids)],
                }
            )
        )
        before = self.env["res.groups"].search_count([])
        hooks.reset_declared_implied_groups(self.env)
        hooks.reset_declared_implied_groups(self.env)
        self.assertEqual(self.env["res.groups"].search_count([]), before)
        self.assertIn(self.env.ref(f"{MODULE}.perm_va05"), manual.group_ids)

    def test_adoption_is_idempotent(self):
        before = self.env["ir.model.data"].search_count([("module", "=", MODULE)])
        hooks.adopt_manual_records(self.env)
        hooks.adopt_manual_records(self.env)
        after = self.env["ir.model.data"].search_count([("module", "=", MODULE)])
        self.assertEqual(before, after)

    def test_standard_menu_links_are_removed(self):
        menu = self.env.ref("account.menu_finance")
        group = self.env.ref(f"{MODULE}.perm_va01")
        menu.group_ids = [Command.link(group.id)]
        hooks.adopt_manual_records(self.env)
        self.assertNotIn(group, menu.group_ids)

    def _create_legacy_field(self):
        return self.env["ir.model.fields"].create(
            {
                "name": hooks.LEGACY_FIELD,
                "model_id": self.env["ir.model"]._get("res.users").id,
                "field_description": "Almacenes/tiendas permitidos",
                "ttype": "many2many",
                "relation": "stock.warehouse",
                "state": "manual",
            }
        )

    def test_legacy_rule_is_adopted_and_view_removed(self):
        self._create_legacy_field()
        rule = self._strip_xmlid("rule_sale_order_allowed_warehouses")
        rule.domain_force = "[('warehouse_id', 'in', user.x_warehouse_ids.ids)]"
        legacy_view = self.env["ir.ui.view"].create(
            {
                "name": "legacy x_warehouse_ids",
                "model": "res.users",
                "inherit_id": self.env.ref("base.view_users_form").id,
                "arch": '<xpath expr="//field[@name=\'group_ids\']" position="before">'
                '<field name="x_warehouse_ids"/></xpath>',
            }
        )
        hooks.adopt_manual_records(self.env)
        self.assertEqual(
            self.env.ref(f"{MODULE}.rule_sale_order_allowed_warehouses"), rule
        )
        self.assertFalse(legacy_view.exists())
        self.assertTrue(
            self.env.ref(f"{MODULE}.view_users_form_allowed_warehouses").exists()
        )

    def test_legacy_field_values_are_copied_and_field_removed(self):
        self._create_legacy_field()
        warehouse = self.env.ref(f"{MODULE}.warehouse_huelva")
        user = self.env["res.users"].create({"name": "Legacy", "login": "legacy_user"})
        user.write({hooks.LEGACY_FIELD: [Command.set(warehouse.ids)]})
        hooks.migrate_legacy_warehouse_field(self.env)
        self.assertEqual(user.allowed_warehouse_ids, warehouse)
        self.assertFalse(
            self.env["ir.model.fields"].search(
                [("model", "=", "res.users"), ("name", "=", hooks.LEGACY_FIELD)]
            )
        )

    def test_migration_without_legacy_field_does_nothing(self):
        hooks.migrate_legacy_warehouse_field(self.env)
