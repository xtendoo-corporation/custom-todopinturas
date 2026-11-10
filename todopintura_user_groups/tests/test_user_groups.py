# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from ast import literal_eval

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import file_path

from ._expected import EXPECTED_ACCESS, EXPECTED_MENUS, MODELS
from .common import TodopinturaTestCase

MODULE = "todopintura_user_groups"

FORBIDDEN_MENUS = [
    "base.menu_administration",  # Ajustes
    "account.menu_finance_configuration",
    "sale.menu_sale_config",
    "stock.menu_stock_config_settings",
    "purchase.menu_purchase_config",
    "hr.menu_hr_root",
    "contacts.menu_contacts",
]


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestTodopinturaUserGroups(TodopinturaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.blocks = cls.env["res.groups"].search(
            [
                (
                    "privilege_id.category_id",
                    "=",
                    cls.env.ref(f"{MODULE}.module_category_todopintura").id,
                )
            ],
            order="sequence",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Test Grupos"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto Test Grupos",
                "type": "consu",
                "list_price": 10,
                "standard_price": 5,
            }
        )

    def _user(self, block_xmlid):
        group = self.env.ref(f"{MODULE}.{block_xmlid}")
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": f"Test {block_xmlid}",
                    "login": f"test_{block_xmlid}",
                    "group_ids": [Command.set(group.ids)],
                }
            )
        )

    def _access(self, user, model):
        return "".join(
            c if self.env[model].with_user(user).has_access(op) else "-"
            for c, op in zip("rwcd", ("read", "write", "create", "unlink"), strict=True)
        )

    # ---- estructura -------------------------------------------------------
    def test_00_structure(self):
        self.assertEqual(len(self.blocks), 10)
        self.assertIn("Dirección", self.blocks.mapped("name"))
        for block in self.blocks.filtered(
            lambda g: "direccion" not in g.get_external_id()[g.id]
        ):
            perms = block.implied_ids.filtered(
                lambda g: (
                    g.get_external_id().get(g.id, "").startswith(f"{MODULE}.perm_")
                )
            )
            self.assertTrue(perms, f"{block.name} no tiene permisos")

    def test_00b_direccion_implies_every_profile(self):
        direccion = self.env.ref(f"{MODULE}.group_10_direccion")
        profiles = self.blocks - direccion
        self.assertEqual(len(profiles), 9)
        self.assertLessEqual(profiles, direccion.all_implied_ids)
        self.assertIn(
            self.env.ref(f"{MODULE}.group_todopintura_restricted"),
            direccion.all_implied_ids,
        )

    def test_00c_group_names_are_unique_and_without_legacy_codes(self):
        module_groups = self.env["ir.model.data"].search(
            [("module", "=", MODULE), ("model", "=", "res.groups")]
        )
        group_names = (
            self.env["res.groups"].browse(module_groups.mapped("res_id")).mapped("name")
        )
        self.assertEqual(len(group_names), len(set(group_names)))
        for name in group_names:
            self.assertNotRegex(name, r"\([A-Z]{1,4}\d+[A-Z0-9]*\)")

    def test_00d_central_price_group_exists_and_is_granted(self):
        group = self.env.ref(f"{MODULE}.perm_m02p_almacen_central")
        central = self.env.ref(f"{MODULE}.group_04_ventas_de_almacen_central")
        self.assertIn(group, central.all_implied_ids)

    # ---- matriz de accesos ------------------------------------------------
    def _exact_acl_only(self):
        """The exact matrix only holds without the customer's extra ACLs."""
        if self.on_full_stack():
            self.skipTest("Exact ACL matrix is checked on the standard stack")

    def test_01_model_access_matrix(self):
        self._exact_acl_only()
        for block_xmlid, expected in EXPECTED_ACCESS.items():
            user = self._user(block_xmlid)
            for model in MODELS:
                self.assertEqual(
                    self._access(user, model),
                    expected[model],
                    f"{block_xmlid} -> {model}",
                )

    # ---- menus ------------------------------------------------------------
    def test_02_visible_menus(self):
        Menu = self.env["ir.ui.menu"]
        for block_xmlid, expected in EXPECTED_MENUS.items():
            user = self._user(block_xmlid)
            visible = Menu.browse(Menu.with_user(user)._visible_menu_ids())
            leaves = {
                xmlid.split(".", 1)[1]
                for xmlid in visible.filtered(lambda m: m.action and not m.child_id).get_external_id().values()
                if xmlid.startswith(f"{MODULE}.")
            }
            self.assertEqual(leaves, set(expected), block_xmlid)
            self.assertEqual(
                len(visible.filtered(lambda m: m.action and not m.child_id)), len(expected), block_xmlid
            )
            visible_xmlids = set(visible.get_external_id().values())
            for forbidden in FORBIDDEN_MENUS:
                self.assertNotIn(
                    forbidden, visible_xmlids, f"{block_xmlid} ve {forbidden}"
                )

    def test_02a_store_profiles_have_no_sale_order_menus(self):
        """Ventas de tiendas is the POS: no quotations or sale orders."""
        Menu = self.env["ir.ui.menu"]
        for xmlid in (
            "group_06_ventas_de_tiendas",
            "group_07_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
        ):
            user = self._user(xmlid)
            visible = Menu.browse(Menu.with_user(user)._visible_menu_ids())
            models = {
                menu.action.res_model
                for menu in visible.filtered(lambda m: m.action and not m.child_id)
                if menu.action._name == "ir.actions.act_window"
            }
            self.assertFalse(
                models & {"sale.order", "sale.order.line", "sale.report"}, xmlid
            )
        store = self.env.ref(f"{MODULE}.group_06_ventas_de_tiendas")
        self.assertNotIn(self.env.ref(f"{MODULE}.perm_va05"), store.all_implied_ids)

    def test_02a2_central_sales_entry_is_the_pos(self):
        """Grabación de ventas of the central warehouse opens the POS dashboard."""
        menu = self.env.ref(f"{MODULE}.menu_vt_sales_entry")
        self.assertEqual(menu.action.res_model, "pos.config")
        group = self._user_with_group("perm_v01")
        for model in ("pos.config", "pos.session", "pos.order"):
            self.assertTrue(self.env[model].with_user(group).has_access("read"), model)
        self.assertTrue(self.env["pos.session"].with_user(group).has_access("create"))

    def _user_with_group(self, xmlid):
        group = self.env.ref(f"{MODULE}.{xmlid}")
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": f"Granular {xmlid}",
                    "login": f"granular_{xmlid}",
                    "group_ids": [Command.set(group.ids)],
                }
            )
        )

    def test_02f_every_root_menu_has_the_todopintura_icon(self):
        icon = "todopintura_user_groups,static/description/icon.png"
        data = self.env["ir.model.data"].search(
            [("module", "=", MODULE), ("model", "=", "ir.ui.menu")]
        )
        roots = (
            self.env["ir.ui.menu"]
            .browse(data.mapped("res_id"))
            .filtered(lambda menu: not menu.parent_id)
        )
        self.assertEqual(len(roots), 5)
        for root in roots:
            self.assertEqual(root.web_icon, icon, root.name)
        self.assertTrue(
            file_path("todopintura_user_groups/static/description/icon.png")
        )

    def test_02b_no_orphan_menus(self):
        """Shared granular groups must not expose children of other profiles' roots."""
        Menu = self.env["ir.ui.menu"]
        user = self._user("group_01_gestion_de_pedidos")
        visible = Menu.browse(Menu.with_user(user)._visible_menu_ids())
        roots = visible.filtered(lambda menu: not menu.parent_id)
        self.assertEqual(roots.mapped("name"), ["Pedidos de clientes"])
        for menu in visible:
            self.assertTrue(menu.parent_id in visible or not menu.parent_id)

    def test_02c_every_menu_has_group_and_ends_in_an_action(self):
        menus = self.env["ir.ui.menu"].search(
            [
                (
                    "id",
                    "in",
                    self.env["ir.model.data"]
                    .search([("module", "=", MODULE), ("model", "=", "ir.ui.menu")])
                    .mapped("res_id"),
                )
            ]
        )
        for menu in menus:
            self.assertTrue(menu.group_ids, f"{menu.complete_name} sin grupo")
            if not menu.child_id:
                self.assertTrue(menu.action, f"{menu.complete_name} sin acción")

    def test_02d_direccion_sees_every_profile_menu(self):
        Menu = self.env["ir.ui.menu"]
        user = self._user("group_10_direccion")
        visible = Menu.browse(Menu.with_user(user)._visible_menu_ids())
        roots = set(visible.filtered(lambda menu: not menu.parent_id).mapped("name"))
        self.assertEqual(
            roots,
            {
                "Pedidos de clientes",
                "Pedidos de y para tiendas",
                "Entradas de proveedor",
                "Ventas de POS",
                "Comerciales",
            },
        )

    def test_02e_standard_menus_are_hidden_for_profiles(self):
        Menu = self.env["ir.ui.menu"]
        for xmlid in ("group_01_gestion_de_pedidos", "group_10_direccion"):
            user = self._user(xmlid)
            visible = Menu.browse(Menu.with_user(user)._visible_menu_ids())
            self.assertFalse(
                visible.filtered(
                    lambda menu: (
                        not menu.get_external_id()[menu.id].startswith(f"{MODULE}.")
                    )
                ),
                xmlid,
            )

    def test_03_admin_not_restricted(self):
        Menu = self.env["ir.ui.menu"]
        admin = self.env.ref("base.user_admin")
        visible = Menu.browse(Menu.with_user(admin)._visible_menu_ids())
        self.assertIn("base.menu_administration", visible.get_external_id().values())

    # ---- flujos reales ----------------------------------------------------
    def test_10_gestion_de_pedidos(self):
        user = self._user("group_01_gestion_de_pedidos")
        order = (
            self.env["sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        Command.create(
                            {"product_id": self.product.id, "product_uom_qty": 2}
                        )
                    ],
                }
            )
        )
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        # lo que NO pueden hacer
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(user).create(
                {"partner_id": self.partner.id}
            )
        with self.assertRaises(AccessError):
            self.env["account.move"].with_user(user).create(
                {"move_type": "out_invoice"}
            )
        with self.assertRaises(AccessError):
            self.product.with_user(user).write({"list_price": 99})
        with self.assertRaises(AccessError):
            self.partner.with_user(user).write({"name": "Otro"})

    def test_11_pedidos_de_y_para_tiendas(self):
        user = self._user("group_02_pedidos_de_y_para_tiendas")
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "internal")], limit=1
        )
        source = picking_type.default_location_src_id
        destination = picking_type.default_location_dest_id
        picking = (
            self.env["stock.picking"]
            .with_user(user)
            .create(
                {
                    "picking_type_id": picking_type.id,
                    "location_id": source.id,
                    "location_dest_id": destination.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": 1,
                                "location_id": source.id,
                                "location_dest_id": destination.id,
                            }
                        )
                    ],
                }
            )
        )
        picking.action_confirm()
        self.assertIn(picking.state, ("confirmed", "assigned", "waiting"))
        with self.assertRaises(AccessError):
            self.env["sale.order"].with_user(user).create(
                {"partner_id": self.partner.id}
            )
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(user).create(
                {"partner_id": self.partner.id}
            )

    def test_12_entradas_de_proveedor(self):
        user = self._user("group_03_gestion_de_entradas_de_proveedor")
        po = (
            self.env["purchase.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_qty": 3,
                                "price_unit": 5,
                            }
                        )
                    ],
                }
            )
        )
        po.button_confirm()
        self.assertEqual(po.state, "purchase")
        # ya no puede mantener productos ni codigos de barras (perfiles bloqueados)
        with self.assertRaises(AccessError):
            self.product.with_user(user).write({"barcode": "TESTGRP0001"})
        with self.assertRaises(AccessError):
            self.env["sale.order"].with_user(user).create(
                {"partner_id": self.partner.id}
            )
        with self.assertRaises(AccessError):
            self.env["account.move"].with_user(user).create({"move_type": "in_invoice"})
        with self.assertRaises(AccessError):
            self.partner.with_user(user).write({"name": "Otro"})

    def test_13_comerciales(self):
        user = self._user("group_08_menu_de_comerciales")
        order = (
            self.env["sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        Command.create(
                            {"product_id": self.product.id, "product_uom_qty": 1}
                        )
                    ],
                }
            )
        )
        self.assertEqual(order.state, "draft")
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(user).create(
                {"partner_id": self.partner.id}
            )
        self.env["sale.report"].with_user(user).search_count([])

    def test_13b_comerciales_see_all_customers_but_only_own_orders(self):
        seller_a = self._user("group_08_menu_de_comerciales")
        seller_b = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Comercial B",
                    "login": "comercial_b",
                    "group_ids": [
                        Command.set(
                            self.env.ref(f"{MODULE}.group_08_menu_de_comerciales").ids
                        )
                    ],
                }
            )
        )
        other_partner = self.env["res.partner"].create(
            {"name": "Cliente de otro comercial"}
        )
        order_a = (
            self.env["sale.order"]
            .with_user(seller_a)
            .create({"partner_id": self.partner.id, "user_id": seller_a.id})
        )
        order_b = (
            self.env["sale.order"]
            .with_user(seller_b)
            .create({"partner_id": other_partner.id, "user_id": seller_b.id})
        )
        orders = self.env["sale.order"].with_user(seller_a).search([])
        self.assertIn(order_a, orders)
        self.assertNotIn(order_b, orders)
        partners = self.env["res.partner"].with_user(seller_a).search([])
        self.assertLessEqual(self.partner | other_partner, partners)

    def test_13c_only_direccion_edits_customers(self):
        editors = {
            "group_08_menu_de_comerciales": False,
            "group_06_ventas_de_tiendas": False,
            "group_10_direccion": True,
            "group_01_gestion_de_pedidos": False,
            "group_03_gestion_de_entradas_de_proveedor": False,
        }
        for xmlid, can_edit in editors.items():
            access = self._access(self._user(xmlid), "res.partner")
            self.assertEqual("w" in access, can_edit, xmlid)

    def test_14_informes_estadisticos(self):
        user = self._user("group_09_informes_estadisticos_menu_of002")
        self.env["sale.report"].with_user(user).search_count([])
        with self.assertRaises(AccessError):
            self.env["res.partner"].with_user(user).create(
                {"name": "Cliente nuevo (M01COM)"}
            )
        with self.assertRaises(AccessError):
            self.env["sale.order"].with_user(user).create(
                {"partner_id": self.partner.id}
            )
        with self.assertRaises(AccessError):
            self.env["stock.picking"].with_user(user).search_count([])

    def test_15_ventas_de_tiendas_tpv(self):
        user = self._user("group_06_ventas_de_tiendas")
        self.assertTrue(self.env["pos.session"].with_user(user).has_access("create"))
        self.assertTrue(self.env["pos.order"].with_user(user).has_access("create"))
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(user).create(
                {"partner_id": self.partner.id}
            )
        with self.assertRaises(AccessError):
            self.env["stock.count"].with_user(user).search_count([])

    def test_16_otras_tiendas_traspasos_y_acuentas(self):
        for xmlid in (
            "group_05_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
            "group_07_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
        ):
            user = self._user(xmlid)
            self.assertTrue(
                self.env["account.payment"].with_user(user).has_access("create")
            )
            self.assertTrue(
                self.env["stock.picking"].with_user(user).has_access("create")
            )
            with self.assertRaises(AccessError):
                self.env["purchase.order"].with_user(user).create(
                    {"partner_id": self.partner.id}
                )
            with self.assertRaises(AccessError):
                self.env["pos.order"].with_user(user).search_count([])

    def test_16b_barcodes_and_prices_only_for_direccion(self):
        editors = {
            "group_03_gestion_de_entradas_de_proveedor": False,
            "group_10_direccion": True,
            "group_01_gestion_de_pedidos": False,
            "group_02_pedidos_de_y_para_tiendas": False,
            "group_04_ventas_de_almacen_central": False,
            "group_06_ventas_de_tiendas": False,
            "group_08_menu_de_comerciales": False,
        }
        pricelist = self.env["product.pricelist"].create({"name": "Tarifa test"})
        for xmlid, allowed in editors.items():
            user = self._user(xmlid)
            for record, values in (
                (self.product, {"barcode": f"BC{xmlid[-6:]}"}),
                (self.product, {"list_price": 12}),
                (pricelist, {"name": "Tarifa editada"}),
            ):
                if allowed:
                    record.with_user(user).write(values)
                else:
                    with self.assertRaises(AccessError, msg=f"{xmlid} {values}"):
                        record.with_user(user).write(values)

    def test_17_combinacion_de_bloques(self):
        """Dos bloques suman sus derechos, nada mas."""
        user = self._user("group_01_gestion_de_pedidos")
        user.group_ids = [
            Command.link(
                self.env.ref(f"{MODULE}.group_03_gestion_de_entradas_de_proveedor").id
            )
        ]
        self.assertEqual(self._access(user, "sale.order"), "rwc-")
        self.assertEqual(self._access(user, "purchase.order"), "rwc-")
        self.assertEqual(self._access(user, "account.move"), "r---")
        self.assertEqual(self._access(user, "pos.order"), "----")

    # ---- flujos de almacen, inventario, TPV e impresion ------------------
    def test_20_recepcion_validada_por_otra_tienda(self):
        user = self._user("group_05_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie")
        storable = self.env["product.product"].create(
            {"name": "Storable Test Grupos", "type": "consu", "is_storable": True}
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {"product_id": storable.id, "product_qty": 3, "price_unit": 1}
                    )
                ],
            }
        )
        po.button_confirm()
        picking = po.picking_ids.with_user(user)
        picking.move_ids.quantity = 3
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    def test_21_ajuste_de_inventario(self):
        user = self._user("group_02_pedidos_de_y_para_tiendas")
        loss = self.env["stock.location"].create(
            {"name": "Perdidas Test", "usage": "inventory"}
        )
        storable = self.env["product.product"].create(
            {
                "name": "Storable Inv Test",
                "type": "consu",
                "is_storable": True,
                "property_stock_inventory": loss.id,
            }
        )
        location = self.env["stock.warehouse"].search([], limit=1).lot_stock_id
        quant = (
            self.env["stock.quant"]
            .with_user(user)
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": storable.id,
                    "location_id": location.id,
                    "inventory_quantity": 5,
                }
            )
        )
        quant.action_apply_inventory()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(storable, location), 5
        )

    def test_22_sesion_tpv_abrir_y_cerrar(self):
        for xmlid in (
            "group_04_ventas_de_almacen_central",
            "group_06_ventas_de_tiendas",
        ):
            user = self._user(xmlid)
            config = self.env["pos.config"].create({"name": f"TPV Test {xmlid}"})
            session = (
                self.env["pos.session"]
                .with_user(user)
                .create({"config_id": config.id, "user_id": user.id})
            )
            session.action_pos_session_open()
            session.action_pos_session_closing_control()
            self.assertEqual(session.state, "closed")

    def test_23_reimprimir_pedido(self):
        user = self._user("group_01_gestion_de_pedidos")
        order = (
            self.env["sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        Command.create(
                            {"product_id": self.product.id, "product_uom_qty": 1}
                        )
                    ],
                }
            )
        )
        html, _fmt = (
            self.env["ir.actions.report"]
            .with_user(user)
            ._render_qweb_html("sale.action_report_saleorder", order.ids)
        )
        self.assertIn(b"Producto Test Grupos", html)

    # ---- usuarios con otros grupos estandar ---------------------------------
    def _check_block_with_extra_groups(self, block_xmlid, extra_groups):
        Menu = self.env["ir.ui.menu"]
        user = self._user(block_xmlid)
        user.group_ids = [Command.link(g.id) for g in extra_groups]
        for model in MODELS:
            self.assertEqual(
                self._access(user, model),
                EXPECTED_ACCESS[block_xmlid][model],
                f"{block_xmlid} + grupos extra -> {model}",
            )
        visible = Menu.browse(Menu.with_user(user)._visible_menu_ids())
        leaves = {
            xmlid.split(".", 1)[1]
            for xmlid in visible.filtered(lambda m: m.action and not m.child_id).get_external_id().values()
            if xmlid.startswith(f"{MODULE}.")
        }
        self.assertEqual(leaves, set(EXPECTED_MENUS[block_xmlid]), block_xmlid)

    def test_30_bloque_mas_grupos_de_administrador(self):
        self._exact_acl_only()
        extra = self.env["res.groups"]
        for xmlid in (
            "sales_team.group_sale_manager",
            "purchase.group_purchase_manager",
            "stock.group_stock_manager",
            "account.group_account_manager",
            "point_of_sale.group_pos_manager",
        ):
            extra |= self.env.ref(xmlid)
        for block_xmlid in EXPECTED_ACCESS:
            self._check_block_with_extra_groups(block_xmlid, extra)

    def test_31_bloque_mas_grupos_de_usuario_real(self):
        self._exact_acl_only()
        real = self.env["res.users"].search([("login", "=", "roque")], limit=1)
        if not real:
            self.skipTest("No existe el usuario 'roque' en esta base")
        # base.group_system / group_erp_manager (administrador de Ajustes) quedan
        # fuera de la restriccion por diseno, asi que no se anaden aqui.
        skip = (f"{MODULE}.", "base.group_system", "base.group_erp_manager")
        extra = real.group_ids.filtered(
            lambda g: not g.get_external_id().get(g.id, "").startswith(skip)
        )
        for block_xmlid in EXPECTED_ACCESS:
            self._check_block_with_extra_groups(block_xmlid, extra)

    def test_02g_every_menu_has_its_own_action(self):
        """No window action is shared by two menus (nor with a standard app), so a
        reload or a link can never open another app."""
        links = self.env["ir.model.data"].search(
            [("module", "=", MODULE), ("model", "=", "ir.ui.menu")]
        )
        Menu = self.env["ir.ui.menu"].with_context(active_test=False)
        for link in links:
            menu = Menu.browse(link.res_id)
            if not menu.action or menu.action._name != "ir.actions.act_window":
                continue
            sharing = Menu.search([("action", "=", f"ir.actions.act_window,{menu.action.id}")])
            self.assertEqual(sharing, menu, f"{link.name} shares its action")
            self.assertEqual(
                menu.action.get_external_id().get(menu.action.id),
                f"{MODULE}.action_{link.name}",
            )

    # ---- bloqueo de precios, descuentos, condiciones y modos de pago --------
    def test_10_locked_profiles_cannot_edit_commercial_data(self):
        """Los 9 perfiles quedan bloqueados; Dirección y administradores no."""
        profiles = [
            xmlid
            for xmlid in EXPECTED_ACCESS
            if xmlid.startswith("group_") and not xmlid.startswith("group_10")
        ]
        for xmlid in profiles:
            user = self._user(xmlid)
            self.assertTrue(user._todopintura_is_locked(), xmlid)
            for model in (
                "res.partner",
                "product.template",
                "product.product",
                "product.pricelist",
                "product.pricelist.item",
                "account.payment.term",
            ):
                for mode in ("write", "create", "unlink"):
                    self.assertFalse(
                        self.env[model].with_user(user).has_access(mode),
                        f"{xmlid} {model} {mode}",
                    )
        director = self._user("group_10_direccion")
        self.assertFalse(director._todopintura_is_locked())
        self.assertTrue(self.env["res.partner"].with_user(director).has_access("write"))
        self.assertFalse(self.env.ref("base.user_admin")._todopintura_is_locked())

    def test_11_locked_user_cannot_change_price_discount_or_terms(self):
        user = self._user("group_01_gestion_de_pedidos")
        director = self._user("group_10_direccion")
        partner = self.env["res.partner"].create({"name": "Cliente lock"})
        product = self.env["product.product"].create({"name": "Prod lock", "list_price": 10})
        term = self.env.ref("account.account_payment_term_30days")
        order = (
            self.env["sale.order"]
            .create(
                {
                    "partner_id": partner.id,
                    "user_id": user.id,
                    "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 1})],
                }
            )
            .sudo()
        )
        line = order.order_line
        base_price, base_term = line.price_unit, order.payment_term_id
        line.with_user(user).write({"price_unit": 1.0, "discount": 50.0})
        order.with_user(user).write({"payment_term_id": term.id})
        self.assertEqual(line.price_unit, base_price)
        self.assertEqual(line.discount, 0.0)
        self.assertEqual(order.payment_term_id, base_term)
        # Dirección sí puede
        line.with_user(director).write({"price_unit": 1.0, "discount": 50.0})
        self.assertEqual(line.price_unit, 1.0)
        self.assertEqual(line.discount, 50.0)

    def test_12_price_consult_wizard(self):
        user = self._user("group_01_gestion_de_pedidos")
        product = self.env["product.product"].create({"name": "Prod consulta", "list_price": 100})
        discounted = self.env["product.pricelist"].create(
            {
                "name": "Tarifa -10%",
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "percentage",
                            "percent_price": 10,
                        }
                    )
                ],
            }
        )
        plain = self.env["product.pricelist"].create({"name": "Tarifa plana"})
        partner_disc = self.env["res.partner"].create(
            {"name": "Cliente con dto", "property_product_pricelist": discounted.id}
        )
        partner_plain = self.env["res.partner"].create(
            {"name": "Cliente sin dto", "property_product_pricelist": plain.id}
        )
        Wizard = self.env["todopintura.price.consult"].with_user(user)
        empty = Wizard.create({"partner_id": partner_disc.id})
        self.assertFalse(empty.ready)
        wiz = Wizard.create({"partner_id": partner_disc.id, "product_id": product.id})
        self.assertTrue(wiz.ready)
        self.assertEqual(wiz.original_price, 100)
        self.assertAlmostEqual(wiz.discount, 10)
        self.assertAlmostEqual(wiz.customer_price, 90)
        wiz = Wizard.create({"partner_id": partner_plain.id, "product_id": product.id})
        self.assertEqual(wiz.discount, 0)
        self.assertEqual(wiz.customer_price, wiz.original_price)

    def test_13_stock_consult_wizard(self):
        user = self._user("group_01_gestion_de_pedidos")
        product = self.env["product.product"].create(
            {"name": "Prod existencias", "is_storable": True, "type": "consu"}
        )
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        # Recepción real de proveedor: genera el movimiento (hoy, no previo a enero).
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 7.0,
                "product_uom": product.uom_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": warehouse.lot_stock_id.id,
            }
        )
        move._action_confirm()
        move.quantity = 7.0
        move.picked = True
        move._action_done()
        Wizard = self.env["todopintura.stock.consult"].with_user(user)
        self.assertFalse(Wizard.create({}).line_ids)
        for period in ("year", "all"):
            wiz = Wizard.create({"product_id": product.id, "period": period})
            lines = wiz.line_ids
            self.assertEqual(
                len(lines), self.env["stock.warehouse"].search_count([])
            )
            line = lines.filtered(lambda line: line.warehouse_id == warehouse)
            self.assertEqual(line.stock_qty, 7.0)
            self.assertEqual(line.prev_qty, 0.0)
            self.assertEqual(line.in_qty, 7.0)

    def test_14b_commercials_own_orders_and_no_confirm(self):
        commercial = self._user("group_08_menu_de_comerciales")
        commercial.is_commercial = True
        other_commercial = self._user("group_09_informes_estadisticos_menu_of002")
        other_commercial.is_commercial = True
        clerk = self._user("group_01_gestion_de_pedidos")
        partner = self.env["res.partner"].create({"name": "Cliente ofertas"})
        Order = self.env["sale.order"]
        own = Order.create({"partner_id": partner.id, "user_id": commercial.id})
        theirs = Order.create({"partner_id": partner.id, "user_id": other_commercial.id})
        clerk_own = Order.create({"partner_id": partner.id, "user_id": clerk.id})
        domain = [("id", "in", (own | theirs | clerk_own).ids)]
        # un comercial solo ve lo suyo
        self.assertEqual(Order.with_user(commercial).search(domain), own)
        # el administrador lo ve todo
        self.assertEqual(
            Order.with_user(self.env.ref("base.user_admin")).search(domain),
            own | theirs | clerk_own,
        )
        # Consulta de ofertas: el perfil no comercial ve los presupuestos de comerciales
        self.assertEqual(Order.with_user(clerk).search(domain), own | theirs | clerk_own)
        # un comercial no puede confirmar, pero el sistema sí
        with self.assertRaises(UserError):
            own.with_user(commercial).action_confirm()
        self.assertEqual(own.state, "draft")

    def test_14c_offers_by_purchasing_show_commercial_quotes(self):
        """«Consulta de ofertas realizadas por compras»: mismos presupuestos de comerciales."""
        commercial = self._user("group_09_informes_estadisticos_menu_of002")
        commercial.is_commercial = True
        partner = self.env["res.partner"].create({"name": "Cliente compras"})
        quote = self.env["sale.order"].create({"partner_id": partner.id, "user_id": commercial.id})
        for xmlid in ("group_05_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",):
            user = self._user(xmlid)
            self.assertEqual(
                self.env["sale.order"].with_user(user).search([("id", "=", quote.id)]), quote, xmlid
            )
        for xmlid in ("menu_vt_transfers_offers", "menu_co_orders", "menu_co_offers"):
            action = self.env.ref(f"{MODULE}.{xmlid}").action
            self.assertEqual(action.res_model, "sale.order")
            self.assertIn("is_commercial", action.domain)

    def test_14d_commercial_makes_quotes_and_only_sees_own_customers(self):
        commercial = self._user("group_08_menu_de_comerciales")
        commercial.is_commercial = True
        Partner = self.env["res.partner"]
        mine = Partner.create({"name": "Cliente mío", "user_id": commercial.id})
        child = Partner.create({"name": "Contacto mío", "parent_id": mine.id, "type": "contact"})
        foreign = Partner.create({"name": "Cliente ajeno"})
        visible = Partner.with_user(commercial).search([("id", "in", (mine | child | foreign).ids)])
        self.assertEqual(visible, mine | child)
        # sus propios contactos y los del sistema siguen siendo legibles
        self.assertTrue(Partner.with_user(commercial).browse(commercial.partner_id.id).name)
        self.assertTrue(Partner.with_user(commercial).browse(self.env.company.partner_id.id).name)
        # administrador: ve todo
        admin_visible = Partner.with_user(self.env.ref("base.user_admin")).search(
            [("id", "in", (mine | child | foreign).ids)]
        )
        self.assertEqual(admin_visible, mine | child | foreign)
        # el comercial puede preparar un presupuesto y leer sus líneas (stock y facturas)
        quote = self.env["sale.order"].with_user(commercial).create(
            {
                "partner_id": mine.id,
                "user_id": commercial.id,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )
        line_fields = [
            name
            for name, field in quote.order_line._fields.items()
            if not field.groups and field.type != "binary"
        ]
        quote.order_line.read(line_fields)
        quote.read(["invoice_ids", "picking_ids", "amount_total"])
        # guardar desde el formulario envía invoice_lines: necesita leer los apuntes contables
        quote.write(
            {
                "order_line": [
                    Command.update(
                        quote.order_line.id,
                        {"product_uom_qty": 2, "invoice_lines": [Command.set([])]},
                    )
                ]
            }
        )
        quote.action_quotation_send()

    # ---- vistas: botones y campos en solo lectura ---------------------------
    def _form_nodes(self, user, model, xpath):
        arch = self.env[model].with_user(user).get_view(view_type="form")["arch"]
        return etree.fromstring(arch).xpath(xpath)

    def test_20_confirm_buttons_are_hidden_for_commercials(self):
        commercial = self._user("group_08_menu_de_comerciales")
        commercial.is_commercial = True
        clerk = self._user("group_01_gestion_de_pedidos")
        buttons = self._form_nodes(commercial, "sale.order", "//button[@name='action_confirm']")
        self.assertEqual(len(buttons), 2)
        for button in buttons:
            self.assertIn("todopintura_is_commercial", button.get("invisible"))
        # la condición se evalúa por usuario: solo el comercial marcado queda bloqueado
        Order = self.env["sale.order"]
        self.assertTrue(Order.with_user(commercial).new({}).todopintura_is_commercial)
        self.assertFalse(Order.with_user(clerk).new({}).todopintura_is_commercial)
        self.assertFalse(
            Order.with_user(self.env.ref("base.user_admin")).new({}).todopintura_is_commercial
        )
        # un administrador marcado como comercial tampoco queda bloqueado
        admin = self.env.ref("base.user_admin")
        admin.is_commercial = True
        self.assertFalse(Order.with_user(admin).new({}).todopintura_is_commercial)

    def test_21_locked_commercial_fields_are_readonly_in_views(self):
        user = self._user("group_01_gestion_de_pedidos")
        self.assertTrue(self.env["sale.order"].with_user(user).new({}).todopintura_locked)
        for name in ("payment_term_id", "payment_mode_id"):
            node = self._form_nodes(user, "sale.order", f"//field[@name='{name}']")[0]
            self.assertIn("todopintura_locked", node.get("readonly"), name)
        price = self._form_nodes(
            user, "sale.order", "//field[@name='order_line']/list//field[@name='price_unit']"
        )[0]
        self.assertIn("parent.todopintura_locked", price.get("readonly"))
        for name in ("invoice_payment_term_id", "payment_mode_id"):
            node = self._form_nodes(user, "account.move", f"//field[@name='{name}']")[0]
            self.assertIn("todopintura_locked", node.get("readonly"), name)
        # Dirección y administradores no quedan bloqueados
        for editor in (self._user("group_10_direccion"), self.env.ref("base.user_admin")):
            self.assertFalse(self.env["sale.order"].with_user(editor).new({}).todopintura_locked)

    # ---- menús de ofertas -----------------------------------------------------
    def test_22_offer_menus_are_visible_and_list_only_commercial_quotes(self):
        Menu = self.env["ir.ui.menu"]
        commercial = self._user("group_09_informes_estadisticos_menu_of002")
        commercial.is_commercial = True
        partner = self.env["res.partner"].create({"name": "Cliente menús ofertas"})
        Order = self.env["sale.order"]
        commercial_quote = Order.create({"partner_id": partner.id, "user_id": commercial.id})
        other_quote = Order.create({"partner_id": partner.id, "user_id": self.env.user.id})
        cases = {
            "menu_pc_offers": "group_01_gestion_de_pedidos",
            "menu_vt_transfers_offers": "group_04_ventas_de_almacen_central",
            "menu_co_orders": "group_08_menu_de_comerciales",
            "menu_co_offers": "group_08_menu_de_comerciales",
        }
        users = {profile: self._user(profile) for profile in set(cases.values())}
        for menu_xmlid, profile in cases.items():
            user = users[profile]
            menu = self.env.ref(f"{MODULE}.{menu_xmlid}")
            self.assertIn(menu.id, Menu.with_user(user)._visible_menu_ids(), menu_xmlid)
            self.assertEqual(menu.action.res_model, "sale.order", menu_xmlid)
            domain = literal_eval(menu.action.domain)
            found = Order.with_user(self.env.ref("base.user_admin")).search(
                domain + [("id", "in", (commercial_quote | other_quote).ids)]
            )
            self.assertEqual(found, commercial_quote, menu_xmlid)

    # ---- TPV ------------------------------------------------------------------
    def test_23_pos_role_is_minimal_for_locked_profiles(self):
        config = self.env["pos.config"].search([], limit=1)
        if not config:
            self.skipTest("Needs a POS config")
        locked = self._user("group_06_ventas_de_tiendas")
        role = self.env["res.users"]._load_pos_data_read(locked, config)[0]["_role"]
        self.assertEqual(role, "minimal")
        for editor in (self._user("group_10_direccion"), self.env.ref("base.user_admin")):
            role = self.env["res.users"]._load_pos_data_read(editor, config)[0]["_role"]
            self.assertNotEqual(role, "minimal", editor.login)

    # ---- «Transferencias internas» (xtendoo_stock_barcode) -------------------------
    def test_24_store_and_supplier_apps_open_transferencias_internas(self):
        Menu = self.env["ir.ui.menu"]
        for menu_xmlid, profile in (
            ("menu_pt_root", "group_02_pedidos_de_y_para_tiendas"),
            ("menu_ep_root", "group_03_gestion_de_entradas_de_proveedor"),
        ):
            menu = self.env.ref(f"{MODULE}.{menu_xmlid}")
            self.assertEqual(menu.action._name, "ir.actions.client", menu_xmlid)
            self.assertEqual(menu.action.tag, "xtendoo_stock_barcode_main_menu", menu_xmlid)
            user = self._user(profile)
            self.assertIn(menu.id, Menu.with_user(user)._visible_menu_ids(), menu_xmlid)
            # lo que hace la pantalla al abrirse y al escanear
            Picking = self.env["stock.picking"].with_user(user)
            self.assertIn("groups", Picking.action_xt_barcode_get_main_menu_data())
            Picking.action_xt_barcode_scan_from_main_menu("CODIGO-INEXISTENTE-123")
            # los submenús de cada perfil siguen colgando de la misma aplicación
            self.assertTrue(menu.child_id, menu_xmlid)

    def test_25_transfer_users_only_see_pedidos_de_y_para_tiendas(self):
        """Usuarios de traspasos (perfiles 02, 05 y 07): sin la aplicación «Ventas de POS»."""
        Menu = self.env["ir.ui.menu"]
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Usuario traspasos",
                "login": "test_traspasos",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref(f"{MODULE}.group_02_pedidos_de_y_para_tiendas").id,
                            self.env.ref(
                                f"{MODULE}.group_05_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie"
                            ).id,
                            self.env.ref(
                                f"{MODULE}.group_07_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie"
                            ).id,
                        ]
                    )
                ],
            }
        )
        visible = Menu.browse(Menu.with_user(user)._visible_menu_ids())
        roots = visible.filtered(lambda m: not m.parent_id)
        self.assertEqual(
            set(roots.get_external_id().values()),
            {f"{MODULE}.menu_pt_root"}
            | {x for x in roots.get_external_id().values() if not x.startswith(f"{MODULE}.")},
        )
        self.assertNotIn(self.env.ref(f"{MODULE}.menu_vt_root"), visible)
        self.assertIn(self.env.ref(f"{MODULE}.menu_pt_transfers_send"), visible)
        # los perfiles de venta no ven la aplicación de traspasos solo por eso
        seller = self._user("group_06_ventas_de_tiendas")
        seller_visible = Menu.browse(Menu.with_user(seller)._visible_menu_ids())
        self.assertIn(self.env.ref(f"{MODULE}.menu_vt_root"), seller_visible)
        self.assertNotIn(self.env.ref(f"{MODULE}.menu_pt_root"), seller_visible)
