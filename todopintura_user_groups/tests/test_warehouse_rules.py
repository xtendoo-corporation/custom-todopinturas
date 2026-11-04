# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

MODULE = "todopintura_user_groups"


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestWarehouseRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env["stock.warehouse"]
        cls.wh_a = Warehouse.create({"name": "Tienda Test A", "code": "TTA"})
        cls.wh_b = Warehouse.create({"name": "Tienda Test B", "code": "TTB"})
        group = cls.env.ref(f"{MODULE}.group_06_ventas_de_tiendas")
        cls.user_a = cls._create_user("shop_a", group, cls.wh_a)
        cls.user_free = cls._create_user("shop_free", group, Warehouse)
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Reglas"})

    @classmethod
    def _create_user(cls, login, group, warehouses):
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "group_ids": [Command.set(group.ids)],
                    "allowed_warehouse_ids": [Command.set(warehouses.ids)],
                }
            )
        )

    def _order(self, warehouse, salesperson):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "user_id": salesperson.id,
            }
        )

    def _picking(self, picking_wh, src_wh, dest_wh):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": picking_wh.int_type_id.id,
                "location_id": src_wh.lot_stock_id.id,
                "location_dest_id": dest_wh.lot_stock_id.id,
            }
        )

    def test_picking_sender_and_receiver_see_the_transfer(self):
        own = self._picking(self.wh_a, self.wh_a, self.wh_a)
        sent = self._picking(self.wh_a, self.wh_a, self.wh_b)
        received = self._picking(self.wh_b, self.wh_b, self.wh_a)
        foreign = self._picking(self.wh_b, self.wh_b, self.wh_b)
        visible = self.env["stock.picking"].with_user(self.user_a).search([])
        expected = own | sent | received
        self.assertEqual(visible & expected, expected)
        self.assertNotIn(foreign, visible)

    def test_picking_location_only_match(self):
        """Source location of the allowed warehouse is enough, whatever the type."""
        picking = self._picking(self.wh_b, self.wh_a, self.wh_b)
        self.assertEqual(picking.picking_type_id.warehouse_id, self.wh_b)
        self.assertIn(
            picking, self.env["stock.picking"].with_user(self.user_a).search([])
        )

    def test_sale_order_limited_to_allowed_warehouses(self):
        order_a = self._order(self.wh_a, self.user_a)
        order_b = self._order(self.wh_b, self.user_a)
        visible = self.env["sale.order"].with_user(self.user_a).search([])
        self.assertIn(order_a, visible)
        self.assertNotIn(order_b, visible)

    def test_pos_sessions_limited_to_allowed_warehouses(self):
        sessions = self.env["pos.session"]
        configs = {}
        for warehouse in (self.wh_a, self.wh_b):
            configs[warehouse] = self.env["pos.config"].create(
                {
                    "name": f"TPV {warehouse.code}",
                    "picking_type_id": warehouse.pos_type_id.id,
                }
            )
            sessions |= self.env["pos.session"].create(
                {"config_id": configs[warehouse].id}
            )
        visible = (
            self.env["pos.session"]
            .with_user(self.user_a)
            .search([("id", "in", sessions.ids)])
        )
        self.assertEqual(visible.config_id, configs[self.wh_a])

    def test_pos_orders_limited_to_allowed_warehouses(self):
        orders = {}
        for warehouse in (self.wh_a, self.wh_b):
            config = self.env["pos.config"].create(
                {
                    "name": f"TPV {warehouse.code}",
                    "picking_type_id": warehouse.pos_type_id.id,
                }
            )
            session = self.env["pos.session"].create({"config_id": config.id})
            orders[warehouse] = self.env["pos.order"].create(
                {
                    "session_id": session.id,
                    "amount_tax": 0,
                    "amount_total": 0,
                    "amount_paid": 0,
                    "amount_return": 0,
                }
            )
        visible = self.env["pos.order"].with_user(self.user_a).search([])
        self.assertIn(orders[self.wh_a], visible)
        self.assertNotIn(orders[self.wh_b], visible)

    def test_empty_field_means_no_restriction(self):
        foreign = self._picking(self.wh_b, self.wh_b, self.wh_b)
        order_b = self._order(self.wh_b, self.user_free)
        self.assertIn(
            foreign, self.env["stock.picking"].with_user(self.user_free).search([])
        )
        self.assertIn(
            order_b, self.env["sale.order"].with_user(self.user_free).search([])
        )

    def test_user_cannot_widen_own_warehouses(self):
        with self.assertRaises(AccessError):
            self.user_a.with_user(self.user_a).write(
                {"allowed_warehouse_ids": [Command.link(self.wh_b.id)]}
            )

    def test_field_is_not_copied_on_duplicate(self):
        copy = self.user_a.copy({"login": "shop_a_copy"})
        self.assertFalse(copy.allowed_warehouse_ids)
