# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import TodopinturaTestCase

MODULE = "todopintura_user_groups"


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestWarehouseRules(TodopinturaTestCase):
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

    def _pricelist(self, config):
        return self.env["product.pricelist"].search(
            [("company_id", "in", [False, config.company_id.id])], limit=1
        ) or self.env["product.pricelist"].create({"name": "Tarifa reglas"})

    def _authorize(self, user, config):
        """Authorize a till when the conventional till filter is installed."""
        if "allowed_pos_config_ids" in user._fields:
            user.allowed_pos_config_ids = [Command.link(config.id)]

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
            if warehouse == self.wh_a:
                self._authorize(self.user_a, configs[warehouse])
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
            if warehouse == self.wh_a:
                self._authorize(self.user_a, config)
            session = self.env["pos.session"].create({"config_id": config.id})
            orders[warehouse] = self.env["pos.order"].create(
                {
                    "session_id": session.id,
                    "pricelist_id": self._pricelist(config).id,
                    "partner_id": self.partner.id,
                    "amount_tax": 0,
                    "amount_total": 0,
                    "amount_paid": 0,
                    "amount_return": 0,
                }
            )
        visible = self.env["pos.order"].with_user(self.user_a).search([])
        self.assertIn(orders[self.wh_a], visible)
        self.assertNotIn(orders[self.wh_b], visible)

    def _session_picking(self, session_wh, picking_wh):
        """Picking born in a POS session of `session_wh` but typed/located in
        `picking_wh` (pickup in another warehouse)."""
        config = self.env["pos.config"].create(
            {
                "name": f"TPV {session_wh.code} {picking_wh.code}",
                "picking_type_id": session_wh.pos_type_id.id,
            }
        )
        session = self.env["pos.session"].create({"config_id": config.id})
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_wh.out_type_id.id,
                "location_id": picking_wh.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "pos_session_id": session.id,
            }
        )
        return session, picking

    def test_remote_pickup_picking_of_own_pos_session_is_readable_only(self):
        """The cashier of store A closes the till with a line picked up in B:
        that picking must be readable (not editable) by the cashier of A."""
        session, picking = self._session_picking(self.wh_a, self.wh_b)
        as_a = picking.with_user(self.user_a)
        self.assertIn(picking, self.env["stock.picking"].with_user(self.user_a).search([]))
        self.assertEqual(as_a.pos_session_id, session)
        self.assertEqual(session.with_user(self.user_a).picking_ids, picking)
        with self.assertRaises(AccessError):
            as_a.write({"origin": "tampering"})
        with self.assertRaises(AccessError):
            as_a.unlink()

    def test_pos_picking_of_another_store_session_stays_hidden(self):
        _session, picking = self._session_picking(self.wh_b, self.wh_b)
        self.assertNotIn(
            picking, self.env["stock.picking"].with_user(self.user_a).search([])
        )
        with self.assertRaises(AccessError):
            picking.with_user(self.user_a).read(["name"])

    # ---- internal transfers: the origin is the user's own warehouse ----------
    def _defaults(self, user, picking_type):
        return (
            self.env["stock.picking"]
            .with_user(user)
            .with_context(default_picking_type_id=picking_type.id)
            .default_get(["picking_type_id", "location_id"])
        )

    def test_internal_transfer_defaults_to_own_warehouse(self):
        for picking_type in (self.wh_a.int_type_id, self.wh_b.int_type_id):
            values = self._defaults(self.user_a, picking_type)
            self.assertEqual(values["picking_type_id"], self.wh_a.int_type_id.id)
            self.assertEqual(
                self.env["stock.location"].browse(values["location_id"]).warehouse_id,
                self.wh_a,
            )

    def test_other_operation_types_keep_their_defaults(self):
        values = self._defaults(self.user_a, self.wh_b.out_type_id)
        self.assertEqual(values["picking_type_id"], self.wh_b.out_type_id.id)

    def test_user_without_restriction_keeps_the_default(self):
        values = self._defaults(self.user_free, self.wh_b.int_type_id)
        self.assertEqual(values["picking_type_id"], self.wh_b.int_type_id.id)

    def test_origin_is_locked_only_with_a_single_warehouse(self):
        internal = self._picking(self.wh_a, self.wh_a, self.wh_b)
        outgoing = self._picking(self.wh_a, self.wh_a, self.wh_b)
        outgoing.picking_type_id = self.wh_a.out_type_id
        group = self.env.ref(f"{MODULE}.group_06_ventas_de_tiendas")
        user_two = self._create_user(
            "shop_two", group, self.wh_a | self.wh_b
        )

        def locked(user, picking):
            return picking.with_user(user).todopintura_origin_locked

        self.assertTrue(locked(self.user_a, internal))
        self.assertFalse(locked(self.user_a, outgoing))
        self.assertFalse(locked(self.user_free, internal))
        self.assertFalse(locked(user_two, internal))

    def test_form_makes_the_origin_readonly_when_locked(self):
        arch = self.env["stock.picking"].get_view(
            self.env.ref("stock.view_picking_form").id, "form"
        )["arch"]
        self.assertIn("todopintura_origin_locked", arch)
        self.assertRegex(
            arch,
            r'name="location_id"[^>]*readonly="state == \'done\' or todopintura_origin_locked"',
        )

    def test_cannot_create_an_internal_transfer_from_another_warehouse(self):
        vals = {
            "picking_type_id": self.wh_a.int_type_id.id,
            "location_id": self.wh_b.lot_stock_id.id,
            "location_dest_id": self.wh_a.lot_stock_id.id,
        }
        Picking = self.env["stock.picking"]
        with self.assertRaises(ValidationError):
            Picking.with_user(self.user_a).create(vals)
        # Own origin works; the system (sudo) and free users are not restricted.
        own = dict(vals, location_id=self.wh_a.lot_stock_id.id,
                   location_dest_id=self.wh_b.lot_stock_id.id)
        self.assertTrue(Picking.with_user(self.user_a).create(own))
        self.assertTrue(Picking.sudo().create(vals))
        self.assertTrue(Picking.with_user(self.user_free).create(vals))

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
