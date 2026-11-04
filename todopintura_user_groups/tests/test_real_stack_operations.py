# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""End-to-end operations of every profile on the customer's full stack."""

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OperationsCase

PROFILE_STORE = "group_06_ventas_de_tiendas"
PROFILE_CENTRAL = "group_04_ventas_de_almacen_central"


class PosOperationsCase(OperationsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls._pos_product()

    @classmethod
    def _pos_product(cls):
        product = cls.env["product.product"].search(
            [
                ("available_in_pos", "=", True),
                ("list_price", ">", 0),
                ("type", "=", "consu"),
            ],
            limit=1,
        )
        if not product:
            product = cls.env["product.product"].create(
                {"name": "Producto e2e", "list_price": 10, "available_in_pos": True}
            )
        return product

    def store_user(
        self, warehouse_xmlid="warehouse_huelva", config_xmlid="pos_config_huelva", **kw
    ):
        return self.make_user(
            PROFILE_STORE,
            login=kw.pop("login", f"e2e_store_{warehouse_xmlid}"),
            warehouses=self.warehouse(warehouse_xmlid),
            configs=self.config(config_xmlid),
        )

    def open_session(self, user, config):
        session = (
            self.env["pos.session"]
            .with_user(user)
            .create({"config_id": config.id, "user_id": user.id})
        )
        session.action_pos_session_open()
        return session

    def pricelist_for(self, config):
        return (
            config.pricelist_id
            or config.available_pricelist_ids[:1]
            or self.env["product.pricelist"].search(
                [("company_id", "in", [False, config.company_id.id])], limit=1
            )
        )

    def cash_method(self, config):
        methods = config.payment_method_ids
        return methods.filtered(lambda m: m.type == "cash")[:1] or methods[:1]

    def ring_up(self, user, session, partner=None, method=None):
        """A complete sale: order with one line, paid, ready to be closed."""
        price = self.product.lst_price
        order = (
            self.env["pos.order"]
            .with_user(user)
            .create(
                {
                    "session_id": session.id,
                    "pricelist_id": self.pricelist_for(session.config_id).id,
                    "partner_id": partner.id if partner else False,
                    "amount_tax": 0,
                    "amount_total": price,
                    "amount_paid": 0,
                    "amount_return": 0,
                    "lines": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "qty": 1,
                                "price_unit": price,
                                "price_subtotal": price,
                                "price_subtotal_incl": price,
                            }
                        )
                    ],
                }
            )
        )
        method = method or self.cash_method(session.config_id)
        order.add_payment(
            {"pos_order_id": order.id, "amount": price, "payment_method_id": method.id}
        )
        order.action_pos_order_paid()
        return order


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestPosSales(PosOperationsCase):
    """Ventas de POS and Ventas de almacén central: the till."""

    def test_store_sells_and_closes_the_till(self):
        user = self.store_user()
        config = self.config("pos_config_huelva")
        session = self.open_session(user, config)
        order = self.ring_up(user, session)
        self.assertEqual(order.state, "paid")
        session.with_user(user).action_pos_session_closing_control()
        self.assertEqual(session.state, "closed")
        self.assertEqual(order.sudo().state, "done")

    def test_store_reprints_and_lists_its_sales(self):
        user = self.store_user()
        session = self.open_session(user, self.config("pos_config_huelva"))
        order = self.ring_up(user, session)
        visible = self.env["pos.order"].with_user(user).search([])
        self.assertIn(order, visible)
        self.assertEqual(self.open_all_menus(user), {})

    def test_store_user_only_sees_its_own_till(self):
        user = self.store_user()
        own = self.config("pos_config_huelva")
        other = self.config("pos_config_ayamonte")
        configs = self.env["pos.config"].with_user(user).search([])
        self.assertIn(own, configs)
        self.assertNotIn(other, configs)
        with self.assertRaises(AccessError):
            other.with_user(user).check_access("read")

    def test_store_cannot_see_other_store_sales(self):
        user_a = self.store_user()
        user_b = self.store_user("warehouse_ayamonte", "pos_config_ayamonte")
        session_b = self.open_session(user_b, self.config("pos_config_ayamonte"))
        order_b = self.ring_up(user_b, session_b)
        self.assertNotIn(order_b, self.env["pos.order"].with_user(user_a).search([]))
        self.assertIn(order_b, self.env["pos.order"].with_user(user_b).search([]))

    def test_central_user_sells_with_its_till(self):
        user = self.make_user(
            PROFILE_CENTRAL,
            login="e2e_central",
            warehouses=self.warehouse("warehouse_central"),
            configs=self.config("pos_config_central_2"),
        )
        session = self.open_session(user, self.config("pos_config_central_2"))
        order = self.ring_up(user, session)
        self.assertEqual(order.state, "paid")
        configs = self.env["pos.config"].with_user(user).search([])
        self.assertEqual(configs, self.config("pos_config_central_2"))
        session.with_user(user).action_pos_session_closing_control()
        self.assertEqual(session.state, "closed")
        self.assertEqual(self.open_all_menus(user), {})

    def test_cash_up_report_wizard_can_be_opened(self):
        user = self.store_user()
        session = self.open_session(user, self.config("pos_config_huelva"))
        self.ring_up(user, session)
        wizard = (
            self.env["pos.daily.sales.reports.wizard"]
            .with_user(user)
            .create({"pos_session_id": session.id})
        )
        self.assertTrue(wizard)


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestPosCredit(PosOperationsCase):
    """Ventas a cuenta: credit policy readable by the store profile."""

    def _credit_order(self, user, session):
        partner = self.env["res.partner"].create(
            {"name": "Cliente a cuenta e2e", "pos_credit_sale_enabled": True}
        )
        order = (
            self.env["pos.order"]
            .with_user(user)
            .create(
                {
                    "session_id": session.id,
                    "pricelist_id": self.pricelist_for(session.config_id).id,
                    "partner_id": partner.id,
                    "amount_tax": 0,
                    "amount_total": 10,
                    "amount_paid": 0,
                    "amount_return": 0,
                    "lines": [
                        Command.create(
                            {
                                "product_id": self.product.id,
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
        return partner, order

    def test_store_reads_the_credit_policy(self):
        user = self.store_user()
        session = self.open_session(user, self.config("pos_config_huelva"))
        _partner, order = self._credit_order(user, session)
        policy = order._get_conventional_credit_policy_data(amount=10)
        self.assertIn("credit_limit", policy)
        order._compute_partner_credit_policy()

    def test_store_opens_credit_customer_form(self):
        user = self.store_user()
        partner = self.env["res.partner"].create(
            {"name": "Cliente crédito form", "pos_credit_sale_enabled": True}
        )
        partner.with_user(user).web_read(
            {"name": {}, "pos_credit_sale_enabled": {}, "pos_order_credit_count": {}}
        )

    def test_credit_sale_lists_show_the_order(self):
        user = self.store_user()
        session = self.open_session(user, self.config("pos_config_huelva"))
        _partner, order = self._credit_order(user, session)
        self.assertIn(order, self.env["pos.order"].with_user(user).search([]))
        self.assertEqual(self.open_all_menus(user), {})
