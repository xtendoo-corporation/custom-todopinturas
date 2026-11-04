# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from ast import literal_eval

from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

MODULE = "todopintura_user_groups"


class TodopinturaCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Extras"})

    @classmethod
    def _user(cls, login, group_xmlid):
        group = cls.env.ref(f"{MODULE}.{group_xmlid}")
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "group_ids": [Command.set(group.ids)],
                }
            )
        )


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestRoutes(TodopinturaCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.seller = cls._user("route_seller", "group_08_menu_de_comerciales")
        cls.route = cls.env["todopintura.route"].create(
            {"name": "Zona Norte", "user_id": cls.seller.id}
        )
        cls.monday = cls.env.ref(f"{MODULE}.weekday_monday")
        cls.tuesday = cls.env.ref(f"{MODULE}.weekday_tuesday")

    def test_weekdays_are_loaded(self):
        days = self.env["todopintura.weekday"].search([])
        self.assertEqual(days.mapped("sequence"), [1, 2, 3, 4, 5, 6, 7])

    def test_partner_route_and_visit_days(self):
        self.partner.write(
            {
                "route_id": self.route.id,
                "visit_day_ids": [Command.set((self.monday | self.tuesday).ids)],
            }
        )
        self.assertEqual(self.partner.route_user_id, self.seller)
        self.assertEqual(self.route.partner_count, 1)

    def test_route_salesperson_change_propagates_to_customers(self):
        self.partner.route_id = self.route
        other = self._user("route_seller_2", "group_08_menu_de_comerciales")
        self.route.user_id = other
        self.assertEqual(self.partner.route_user_id, other)

    def test_zone_is_unique_per_salesperson(self):
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(IntegrityError),
            self.env.cr.savepoint(),
        ):
            self.env["todopintura.route"].create(
                {"name": "Zona Norte", "user_id": self.seller.id}
            )

    def test_planning_groups_customers_by_salesperson_and_day(self):
        self.partner.write(
            {
                "route_id": self.route.id,
                "visit_day_ids": [Command.set((self.monday | self.tuesday).ids)],
            }
        )
        groups = self.env["res.partner"]._read_group(
            [("route_id", "!=", False)],
            ["route_user_id", "visit_day_ids"],
            ["__count"],
        )
        self.assertEqual(
            {(user.id, day.id): count for user, day, count in groups},
            {(self.seller.id, self.monday.id): 1, (self.seller.id, self.tuesday.id): 1},
        )

    def test_planning_action_only_lists_routed_customers(self):
        self.partner.route_id = self.route
        action = self.env.ref(f"{MODULE}.action_route_planning")
        found = self.env["res.partner"].search(literal_eval(action.domain))
        self.assertIn(self.partner, found)
        other = self.env["res.partner"].create({"name": "Sin ruta"})
        self.assertNotIn(other, found)

    def test_only_commercials_maintain_routes(self):
        route = (
            self.env["todopintura.route"]
            .with_user(self.seller)
            .create({"name": "Zona Sur", "user_id": self.seller.id})
        )
        self.assertTrue(route)
        shop = self._user("route_shop", "group_06_ventas_de_tiendas")
        with self.assertRaises(AccessError):
            self.env["todopintura.route"].with_user(shop).create(
                {"name": "Zona Este", "user_id": self.seller.id}
            )
        self.assertTrue(self.env["todopintura.route"].with_user(shop).search([]))


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestCommissions(TodopinturaCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.seller_a = cls._user("comm_a", "group_08_menu_de_comerciales")
        cls.seller_b = cls._user("comm_b", "group_08_menu_de_comerciales")
        cls.direccion = cls._user("comm_dir", "group_10_direccion")
        cls.categ = cls.env["product.category"].create({"name": "Pinturas test"})
        cls.other_categ = cls.env["product.category"].create({"name": "Otros test"})
        cls.product = cls.env["product.product"].create(
            {"name": "Esmalte", "list_price": 100, "categ_id": cls.categ.id}
        )
        cls.order_a = cls._order(cls.seller_a, 3)
        cls.order_b = cls._order(cls.seller_b, 1)

    @classmethod
    def _order(cls, salesperson, qty):
        order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "user_id": salesperson.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": qty,
                            "price_unit": 100,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        return order

    def _rows(self, user=None):
        report = self.env["todopintura.commission.report"]
        if user:
            report = report.with_user(user)
        return report.search([("order_id", "in", (self.order_a | self.order_b).ids)])

    def _row(self, order):
        self.env.invalidate_all()
        return self._rows().filtered(lambda row: row.order_id == order)

    def test_without_rates_no_commission_is_invented(self):
        row = self._row(self.order_a)
        self.assertEqual(row.price_subtotal, 300)
        self.assertFalse(row.rate)
        self.assertEqual(row.commission, 0)

    def test_salesperson_rate(self):
        self.env["todopintura.commission.rate"].create(
            {"user_id": self.seller_a.id, "rate": 10}
        )
        self.assertEqual(self._row(self.order_a).commission, 30)
        self.assertEqual(self._row(self.order_b).commission, 0)

    def test_category_rate_applies_to_everybody(self):
        self.env["todopintura.commission.rate"].create(
            {"categ_id": self.categ.id, "rate": 5}
        )
        self.assertEqual(self._row(self.order_a).commission, 15)
        self.assertEqual(self._row(self.order_b).commission, 5)

    def test_most_specific_rate_wins(self):
        Rate = self.env["todopintura.commission.rate"]
        Rate.create({"categ_id": self.categ.id, "rate": 5})
        Rate.create({"user_id": self.seller_a.id, "rate": 10})
        self.assertEqual(self._row(self.order_a).rate, 10)
        Rate.create(
            {"user_id": self.seller_a.id, "categ_id": self.categ.id, "rate": 12}
        )
        self.assertEqual(self._row(self.order_a).rate, 12)
        self.assertEqual(self._row(self.order_b).rate, 5)

    def test_rate_for_another_category_is_ignored(self):
        self.env["todopintura.commission.rate"].create(
            {"categ_id": self.other_categ.id, "rate": 9}
        )
        self.assertFalse(self._row(self.order_a).rate)

    def test_inactive_and_out_of_period_rates_are_ignored(self):
        Rate = self.env["todopintura.commission.rate"]
        Rate.create({"user_id": self.seller_a.id, "rate": 10, "active": False})
        Rate.create({"user_id": self.seller_a.id, "rate": 10, "date_to": "2000-01-01"})
        self.assertFalse(self._row(self.order_a).rate)

    def test_salesperson_only_sees_own_sales(self):
        rows = self._rows(self.seller_a)
        self.assertEqual(rows.order_id, self.order_a)

    def test_direccion_sees_every_salesperson(self):
        self.assertEqual(
            self._rows(self.direccion).order_id, self.order_a | self.order_b
        )

    def test_rate_validations(self):
        Rate = self.env["todopintura.commission.rate"]
        with self.assertRaises(ValidationError):
            Rate.create({"rate": 10})
        with self.assertRaises(ValidationError):
            Rate.create({"user_id": self.seller_a.id, "rate": 101})
        with self.assertRaises(ValidationError):
            Rate.create({"user_id": self.seller_a.id, "rate": -1})
        with self.assertRaises(ValidationError):
            Rate.create(
                {
                    "user_id": self.seller_a.id,
                    "rate": 1,
                    "date_from": "2026-02-01",
                    "date_to": "2026-01-01",
                }
            )

    def test_only_direccion_maintains_rates(self):
        Rate = self.env["todopintura.commission.rate"]
        Rate.with_user(self.direccion).create({"user_id": self.seller_a.id, "rate": 3})
        with self.assertRaises(AccessError):
            Rate.with_user(self.seller_a).create(
                {"user_id": self.seller_a.id, "rate": 3}
            )

    def test_draft_orders_are_not_reported(self):
        draft = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "user_id": self.seller_a.id,
                "order_line": [Command.create({"product_id": self.product.id})],
            }
        )
        report = self.env["todopintura.commission.report"]
        self.assertFalse(report.search([("order_id", "=", draft.id)]))


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestPurchaseHistory(TodopinturaCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["product.product"].create(
            {"name": "Servicio historial", "type": "service", "list_price": 50}
        )
        cls.contact = cls.env["res.partner"].create(
            {"name": "Contacto", "parent_id": cls.partner.id}
        )

    def _order(self, partner, delivered=0):
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    Command.create(
                        {"product_id": self.service.id, "product_uom_qty": 2}
                    )
                ],
            }
        )
        order.action_confirm()
        order.order_line.qty_delivered = delivered
        return order

    def _history(self, order):
        action = order.action_open_purchase_history()
        lines = self.env[action["res_model"]].search(action["domain"])
        return action, lines

    def test_history_shows_previous_delivered_lines_only(self):
        delivered = self._order(self.partner, delivered=2)
        self._order(self.partner, delivered=0)
        current = self._order(self.partner)
        _action, lines = self._history(current)
        self.assertEqual(lines.order_id, delivered)

    def test_history_includes_the_company_contacts(self):
        delivered = self._order(self.contact, delivered=1)
        current = self._order(self.partner)
        self.assertEqual(self._history(current)[1].order_id, delivered)

    def test_history_excludes_other_customers_and_current_order(self):
        other = self.env["res.partner"].create({"name": "Otro cliente"})
        self._order(other, delivered=2)
        current = self._order(self.partner, delivered=2)
        self.assertFalse(self._history(current)[1])

    def test_history_action_is_grouped_by_product_and_read_only(self):
        current = self._order(self.partner)
        action, _lines = self._history(current)
        self.assertEqual(action["context"]["group_by"], ["product_id"])
        self.assertEqual([view[1] for view in action["views"]], ["list", "pivot"])

    def test_history_button_is_in_the_order_form(self):
        arch = self.env["sale.order"].get_view(view_type="form")["arch"]
        self.assertIn("action_open_purchase_history", arch)
