# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ._expected import EXPECTED_ACCESS, EXPECTED_MENUS, MODELS

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
class TestTodopinturaUserGroups(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.blocks = cls.env["res.groups"].search(
            [("privilege_id.category_id", "=", cls.env.ref(f"{MODULE}.module_category_todopintura").id)],
            order="sequence",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Test Grupos"})
        cls.product = cls.env["product.product"].create(
            {"name": "Producto Test Grupos", "type": "consu", "list_price": 10, "standard_price": 5}
        )

    def _user(self, block_xmlid):
        group = self.env.ref(f"{MODULE}.{block_xmlid}")
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": f"Test {block_xmlid}",
                "login": f"test_{block_xmlid}",
                "group_ids": [Command.set(group.ids)],
            }
        )

    def _access(self, user, model):
        return "".join(
            c if self.env[model].with_user(user).has_access(op) else "-"
            for c, op in zip("rwcd", ("read", "write", "create", "unlink"), strict=True)
        )

    # ---- estructura -------------------------------------------------------
    def test_00_structure(self):
        self.assertEqual(len(self.blocks), 9)
        names = self.blocks.mapped("name")
        self.assertEqual(sum("MENU VA80" in n for n in names), 2)
        for block in self.blocks:
            perms = block.implied_ids.filtered(
                lambda g: g.get_external_id().get(g.id, "").startswith(f"{MODULE}.perm_")
            )
            self.assertTrue(perms, f"{block.name} no tiene permisos")

    # ---- matriz de accesos ------------------------------------------------
    def test_01_model_access_matrix(self):
        for block_xmlid, expected in EXPECTED_ACCESS.items():
            user = self._user(block_xmlid)
            for model in MODELS:
                self.assertEqual(
                    self._access(user, model), expected[model], f"{block_xmlid} -> {model}"
                )

    # ---- menus ------------------------------------------------------------
    def test_02_visible_menus(self):
        Menu = self.env["ir.ui.menu"]
        for block_xmlid, expected in EXPECTED_MENUS.items():
            user = self._user(block_xmlid)
            visible = Menu.browse(Menu.with_user(user)._visible_menu_ids())
            leaves = set(visible.filtered("action").get_external_id().values())
            self.assertEqual(leaves, set(expected), block_xmlid)
            visible_xmlids = set(visible.get_external_id().values())
            for forbidden in FORBIDDEN_MENUS:
                self.assertNotIn(forbidden, visible_xmlids, f"{block_xmlid} ve {forbidden}")

    def test_03_admin_not_restricted(self):
        Menu = self.env["ir.ui.menu"]
        admin = self.env.ref("base.user_admin")
        visible = Menu.browse(Menu.with_user(admin)._visible_menu_ids())
        self.assertIn("base.menu_administration", visible.get_external_id().values())

    # ---- flujos reales ----------------------------------------------------
    def test_10_gestion_de_pedidos(self):
        user = self._user("group_01_gestion_de_pedidos")
        order = self.env["sale.order"].with_user(user).create(
            {
                "partner_id": self.partner.id,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 2})],
            }
        )
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        # lo que NO pueden hacer
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(user).create({"partner_id": self.partner.id})
        with self.assertRaises(AccessError):
            self.env["account.move"].with_user(user).create({"move_type": "out_invoice"})
        with self.assertRaises(AccessError):
            self.product.with_user(user).write({"list_price": 99})
        with self.assertRaises(AccessError):
            self.partner.with_user(user).write({"name": "Otro"})

    def test_11_pedidos_de_y_para_tiendas(self):
        user = self._user("group_02_pedidos_de_y_para_tiendas")
        picking_type = self.env["stock.picking.type"].search([("code", "=", "internal")], limit=1)
        picking = self.env["stock.picking"].with_user(user).create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "location_id": picking_type.default_location_src_id.id,
                            "location_dest_id": picking_type.default_location_dest_id.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        self.assertIn(picking.state, ("confirmed", "assigned", "waiting"))
        with self.assertRaises(AccessError):
            self.env["sale.order"].with_user(user).create({"partner_id": self.partner.id})
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(user).create({"partner_id": self.partner.id})

    def test_12_entradas_de_proveedor(self):
        user = self._user("group_03_gestion_de_entradas_de_proveedor")
        po = self.env["purchase.order"].with_user(user).create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create({"product_id": self.product.id, "product_qty": 3, "price_unit": 5})
                ],
            }
        )
        po.button_confirm()
        self.assertEqual(po.state, "purchase")
        # mantenimiento de codigos de barras (M020)
        self.product.with_user(user).write({"barcode": "TESTGRP0001"})
        with self.assertRaises(AccessError):
            self.env["sale.order"].with_user(user).create({"partner_id": self.partner.id})
        with self.assertRaises(AccessError):
            self.env["account.move"].with_user(user).create({"move_type": "in_invoice"})
        with self.assertRaises(AccessError):
            self.partner.with_user(user).write({"name": "Otro"})

    def test_13_comerciales(self):
        user = self._user("group_08_menu_de_comerciales")
        order = self.env["sale.order"].with_user(user).create(
            {
                "partner_id": self.partner.id,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )
        self.assertEqual(order.state, "draft")
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(user).create({"partner_id": self.partner.id})
        with self.assertRaises(AccessError):
            self.env["sale.report"].with_user(user).search_count([])

    def test_14_informes_estadisticos(self):
        user = self._user("group_09_informes_estadisticos_menu_of002")
        self.env["sale.report"].with_user(user).search_count([])
        self.env["res.partner"].with_user(user).create({"name": "Cliente nuevo (M01COM)"})
        with self.assertRaises(AccessError):
            self.env["sale.order"].with_user(user).create({"partner_id": self.partner.id})
        with self.assertRaises(AccessError):
            self.env["stock.picking"].with_user(user).search_count([])

    def test_15_ventas_de_tiendas_tpv(self):
        user = self._user("group_06_ventas_de_tiendas")
        self.assertTrue(self.env["pos.session"].with_user(user).has_access("create"))
        self.assertTrue(self.env["pos.order"].with_user(user).has_access("create"))
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(user).create({"partner_id": self.partner.id})
        with self.assertRaises(AccessError):
            self.env["stock.count"].with_user(user).search_count([])

    def test_16_otras_tiendas_traspasos_y_acuentas(self):
        for xmlid in (
            "group_05_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
            "group_07_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
        ):
            user = self._user(xmlid)
            self.assertTrue(self.env["account.payment"].with_user(user).has_access("create"))
            self.assertTrue(self.env["stock.picking"].with_user(user).has_access("create"))
            with self.assertRaises(AccessError):
                self.env["purchase.order"].with_user(user).create({"partner_id": self.partner.id})
            with self.assertRaises(AccessError):
                self.env["pos.order"].with_user(user).search_count([])

    def test_17_combinacion_de_bloques(self):
        """Dos bloques suman sus derechos, nada mas."""
        user = self._user("group_01_gestion_de_pedidos")
        user.group_ids = [Command.link(self.env.ref(f"{MODULE}.group_03_gestion_de_entradas_de_proveedor").id)]
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
                "order_line": [Command.create({"product_id": storable.id, "product_qty": 3, "price_unit": 1})],
            }
        )
        po.button_confirm()
        picking = po.picking_ids.with_user(user)
        picking.move_ids.quantity = 3
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    def test_21_ajuste_de_inventario(self):
        user = self._user("group_02_pedidos_de_y_para_tiendas")
        loss = self.env["stock.location"].create({"name": "Perdidas Test", "usage": "inventory"})
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
            .create({"product_id": storable.id, "location_id": location.id, "inventory_quantity": 5})
        )
        quant.action_apply_inventory()
        self.assertEqual(self.env["stock.quant"]._get_available_quantity(storable, location), 5)

    def test_22_sesion_tpv_abrir_y_cerrar(self):
        for xmlid in ("group_04_ventas_de_almacen_central", "group_06_ventas_de_tiendas"):
            user = self._user(xmlid)
            config = self.env["pos.config"].create({"name": f"TPV Test {xmlid}"})
            session = self.env["pos.session"].with_user(user).create(
                {"config_id": config.id, "user_id": user.id}
            )
            session.action_pos_session_open()
            session.action_pos_session_closing_control()
            self.assertEqual(session.state, "closed")

    def test_23_reimprimir_pedido(self):
        user = self._user("group_01_gestion_de_pedidos")
        order = self.env["sale.order"].with_user(user).create(
            {
                "partner_id": self.partner.id,
                "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1})],
            }
        )
        html, _fmt = self.env["ir.actions.report"].with_user(user)._render_qweb_html(
            "sale.action_report_saleorder", order.ids
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
        leaves = set(visible.filtered("action").get_external_id().values())
        self.assertEqual(leaves, set(EXPECTED_MENUS[block_xmlid]), block_xmlid)

    def test_30_bloque_mas_grupos_de_administrador(self):
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
