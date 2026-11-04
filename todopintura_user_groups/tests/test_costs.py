# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import TodopinturaTestCase

MODULE = "todopintura_user_groups"

HIDDEN_FOR_STANDARD_USERS = (
    # (model, view type, field name)
    ("product.template", "form", "standard_price"),
    ("product.template", "list", "standard_price"),
    ("product.template", "form", "seller_ids"),
    ("product.product", "list", "standard_price"),
    ("product.supplierinfo", "list", "price"),
    ("product.supplierinfo", "form", "price"),
    ("pos.order", "form", "margin"),
    ("pos.order", "form", "total_cost"),
    ("pos.order", "pivot", "margin"),
)


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestCostVisibility(TodopinturaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = {
            xmlid: cls._create_user(xmlid)
            for xmlid in (
                "group_01_gestion_de_pedidos",
                "group_06_ventas_de_tiendas",
                "group_08_menu_de_comerciales",
                "group_03_gestion_de_entradas_de_proveedor",
                "group_10_direccion",
            )
        }
        cls.hidden_users = [
            cls.users[key]
            for key in (
                "group_01_gestion_de_pedidos",
                "group_06_ventas_de_tiendas",
                "group_08_menu_de_comerciales",
            )
        ]
        cls.cost_users = [
            cls.users["group_03_gestion_de_entradas_de_proveedor"],
            cls.users["group_10_direccion"],
            cls.env.ref("base.user_admin"),
        ]

    @classmethod
    def _create_user(cls, xmlid):
        group = cls.env.ref(f"{MODULE}.{xmlid}")
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": f"Costs {xmlid}",
                    "login": f"costs_{xmlid}",
                    "group_ids": [Command.set(group.ids)],
                }
            )
        )

    def _has_node(self, user, model, view_type, field):
        arch = self.env[model].with_user(user).get_view(view_type=view_type)["arch"]
        return f'name="{field}"' in arch

    def _readers(self, users, model):
        return [
            user for user in users if self.env[model].with_user(user).has_access("read")
        ]

    def test_costs_hidden_for_users_without_the_group(self):
        for model, view_type, field in HIDDEN_FOR_STANDARD_USERS:
            readers = self._readers(self.hidden_users, model)
            self.assertTrue(readers, f"nadie lee {model}")
            for user in readers:
                self.assertFalse(
                    self._has_node(user, model, view_type, field),
                    f"{user.login} ve {field} en {model}/{view_type}",
                )

    def test_costs_visible_for_suppliers_direccion_and_admin(self):
        for model, view_type, field in HIDDEN_FOR_STANDARD_USERS:
            if (model, view_type, field) == ("pos.order", "form", "total_cost"):
                continue  # only shown when the order total cost is computed
            readers = self._readers(self.cost_users, model)
            self.assertTrue(readers, f"nadie lee {model}")
            for user in readers:
                self.assertTrue(
                    self._has_node(user, model, view_type, field),
                    f"{user.login} no ve {field} en {model}/{view_type}",
                )

    def test_margin_fields_are_not_available_as_measures(self):
        for model in ("report.pos.order", "pos.order", "pos.order.line"):
            for user in self.hidden_users:
                fields = self.env[model].with_user(user).fields_get(["margin"])
                self.assertFalse(fields, f"{user.login}: {model}.margin")
            fields = (
                self.env[model].with_user(self.cost_users[0]).fields_get(["margin"])
            )
            self.assertIn("margin", fields)

    def test_variant_edit_form_hides_cost(self):
        view = self.env.ref("product.product_variant_easy_edit_view")
        for user in self.hidden_users:
            arch = (
                self.env["product.product"]
                .with_user(user)
                .get_view(view_id=view.id, view_type="form")["arch"]
            )
            self.assertNotIn('name="standard_price"', arch)
        arch = (
            self.env["product.product"]
            .with_user(self.cost_users[0])
            .get_view(view_id=view.id, view_type="form")["arch"]
        )
        self.assertIn('name="standard_price"', arch)

    def test_stock_valuation_columns_are_hidden(self):
        for user in self.hidden_users:
            arch = (
                self.env["product.product"]
                .with_user(user)
                .get_view(
                    view_id=self.env.ref(
                        "stock_account.product_product_stock_tree_inherit_stock_account"
                    ).id,
                    view_type="list",
                )["arch"]
            )
            self.assertNotIn('name="avg_cost"', arch)
            self.assertNotIn('name="total_value"', arch)

    def test_cost_group_membership(self):
        group = self.env.ref(f"{MODULE}.group_cost_viewer")
        for key, expected in (
            ("group_03_gestion_de_entradas_de_proveedor", True),
            ("group_10_direccion", True),
            ("group_01_gestion_de_pedidos", False),
            ("group_04_ventas_de_almacen_central", False),
            ("group_06_ventas_de_tiendas", False),
            ("group_08_menu_de_comerciales", False),
        ):
            profile = self.env.ref(f"{MODULE}.{key}")
            self.assertEqual(group in profile.all_implied_ids, expected, key)
        self.assertIn(group, self.env.ref("base.group_system").all_implied_ids)

    def test_pos_order_can_be_created_without_margin_access(self):
        user = self.users["group_06_ventas_de_tiendas"]
        product = self.env["product.product"].create(
            {
                "name": "Producto TPV costes",
                "list_price": 10,
                "standard_price": 4,
                "taxes_id": [Command.clear()],
            }
        )
        config = self.env["pos.config"].create({"name": "TPV costes"})
        if "allowed_pos_config_ids" in user._fields:
            user.allowed_pos_config_ids = [Command.link(config.id)]
        pricelist = self.env["product.pricelist"].search(
            [("company_id", "in", [False, config.company_id.id])], limit=1
        ) or self.env["product.pricelist"].create({"name": "Tarifa costes"})
        customer = self.env["res.partner"].create({"name": "Cliente TPV costes"})
        session = (
            self.env["pos.session"]
            .with_user(user)
            .create({"config_id": config.id, "user_id": user.id})
        )
        order = (
            self.env["pos.order"]
            .with_user(user)
            .create(
                {
                    "session_id": session.id,
                    "pricelist_id": pricelist.id,
                    "partner_id": customer.id,
                    "amount_tax": 0,
                    "amount_total": 10,
                    "amount_paid": 0,
                    "amount_return": 0,
                    "lines": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "qty": 1,
                                "price_unit": 10,
                                "price_subtotal": 10,
                                "price_subtotal_incl": 10,
                            }
                        )
                    ],
                }
            )
        )
        self.assertEqual(order.amount_total, 10)
        with self.assertRaises(AccessError):
            order.margin  # noqa: B018
        self.assertTrue(order.sudo().lines)

    def test_normal_flows_still_work_without_cost_access(self):
        """Hiding costs must not break sales or POS order handling."""
        seller = self.users["group_08_menu_de_comerciales"]
        partner = self.env["res.partner"].create({"name": "Cliente costes"})
        product = self.env["product.product"].create(
            {"name": "Producto costes", "list_price": 10, "standard_price": 4}
        )
        order = (
            self.env["sale.order"]
            .with_user(seller)
            .create(
                {
                    "partner_id": partner.id,
                    "order_line": [
                        Command.create({"product_id": product.id, "product_uom_qty": 2})
                    ],
                }
            )
        )
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.amount_untaxed, 20)
        self.assertEqual(product.standard_price, 4)
