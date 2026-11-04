# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Stock, purchasing, sales and management operations on the full stack."""

from ast import literal_eval

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import OperationsCase


class StockOperationsCase(OperationsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Pintura e2e",
                "is_storable": True,
                "list_price": 20,
                "standard_price": 8,
            }
        )

    def stock_in(self, warehouse, qty):
        self.env["stock.quant"].sudo()._update_available_quantity(
            self.product, warehouse.lot_stock_id, qty
        )

    def transfer(self, user, source, destination, qty=2):
        picking = (
            self.env["stock.picking"]
            .with_user(user)
            .create(
                {
                    "picking_type_id": source.int_type_id.id,
                    "location_id": source.lot_stock_id.id,
                    "location_dest_id": destination.lot_stock_id.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": qty,
                                "location_id": source.lot_stock_id.id,
                                "location_dest_id": destination.lot_stock_id.id,
                            }
                        )
                    ],
                }
            )
        )
        picking.action_confirm()
        picking.action_assign()
        return picking

    def on_hand(self, warehouse):
        return self.env["stock.quant"]._get_available_quantity(
            self.product, warehouse.lot_stock_id
        )


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestStoreTransfers(StockOperationsCase):
    """Traspasos entre tiendas: direct, one step, visible to origin and destination."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.huelva = cls.warehouse("warehouse_huelva")
        cls.ayamonte = cls.warehouse("warehouse_ayamonte")
        cls.bermejales = cls.warehouse("warehouse_bermejales")
        cls.user_huelva = cls.make_user(
            "group_06_ventas_de_tiendas", "e2e_huelva", cls.huelva
        )
        cls.user_ayamonte = cls.make_user(
            "group_06_ventas_de_tiendas", "e2e_ayamonte", cls.ayamonte
        )
        cls.user_bermejales = cls.make_user(
            "group_06_ventas_de_tiendas", "e2e_bermejales", cls.bermejales
        )

    def test_send_and_receive_between_stores(self):
        self.stock_in(self.huelva, 10)
        picking = self.transfer(self.user_huelva, self.huelva, self.ayamonte)
        self.assertEqual(picking.state, "assigned")
        picking.move_ids.quantity = 2
        picking.with_user(self.user_huelva).button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self.on_hand(self.huelva), 8)
        self.assertEqual(self.on_hand(self.ayamonte), 2)

    def test_origin_and_destination_see_it_but_a_third_store_does_not(self):
        self.stock_in(self.huelva, 10)
        picking = self.transfer(self.user_huelva, self.huelva, self.ayamonte)
        Picking = self.env["stock.picking"]
        self.assertIn(picking, Picking.with_user(self.user_huelva).search([]))
        self.assertIn(picking, Picking.with_user(self.user_ayamonte).search([]))
        self.assertNotIn(picking, Picking.with_user(self.user_bermejales).search([]))
        with self.assertRaises(AccessError):
            picking.with_user(self.user_bermejales).check_access("read")

    def test_destination_confirms_the_reception(self):
        self.stock_in(self.huelva, 10)
        picking = self.transfer(self.user_huelva, self.huelva, self.ayamonte)
        picking.move_ids.quantity = 2
        picking.with_user(self.user_ayamonte).button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self.on_hand(self.ayamonte), 2)

    def test_pending_transfers_menu_lists_it(self):
        self.stock_in(self.huelva, 10)
        picking = self.transfer(self.user_huelva, self.huelva, self.ayamonte)
        action = self.env.ref("todopintura_user_groups.action_transfers_pending")
        domain = literal_eval(action.domain)
        found = self.env["stock.picking"].with_user(self.user_ayamonte).search(domain)
        self.assertIn(picking, found)
        self.assertEqual(self.open_all_menus(self.user_huelva), {})
        self.assertEqual(self.open_all_menus(self.user_ayamonte), {})


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestWarehouseOperations(StockOperationsCase):
    """Pedidos de y para tiendas: movement notes, replenishment and inventory."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.huelva = cls.warehouse("warehouse_huelva")
        cls.user = cls.make_user(
            "group_02_pedidos_de_y_para_tiendas", "e2e_wh", cls.huelva
        )

    def test_internal_movement_note_is_validated(self):
        self.stock_in(self.huelva, 5)
        picking = self.transfer(
            self.user, self.huelva, self.warehouse("warehouse_ayamonte"), 1
        )
        picking.move_ids.quantity = 1
        picking.with_user(self.user).button_validate()
        self.assertEqual(picking.state, "done")

    def test_physical_inventory_adjustment(self):
        quant = (
            self.env["stock.quant"]
            .with_user(self.user)
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": self.product.id,
                    "location_id": self.huelva.lot_stock_id.id,
                    "inventory_quantity": 7,
                }
            )
        )
        quant.action_apply_inventory()
        self.assertEqual(self.on_hand(self.huelva), 7)

    def test_replenishment_rule_is_listed(self):
        rule = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "location_id": self.huelva.lot_stock_id.id,
                "product_min_qty": 1,
                "product_max_qty": 5,
            }
        )
        self.assertIn(
            rule, self.env["stock.warehouse.orderpoint"].with_user(self.user).search([])
        )

    def test_all_menus_open(self):
        self.assertEqual(self.open_all_menus(self.user), {})


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestPurchasingOperations(StockOperationsCase):
    """Entradas de proveedor: order, receive, barcode, prices and costs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.make_user(
            "group_03_gestion_de_entradas_de_proveedor", "e2e_buyer"
        )
        cls.supplier = cls.env["res.partner"].create(
            {"name": "Proveedor e2e", "supplier_rank": 1}
        )

    def _order(self):
        order = (
            self.env["purchase.order"]
            .with_user(self.user)
            .create(
                {
                    "partner_id": self.supplier.id,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_qty": 4,
                                "price_unit": 6,
                            }
                        )
                    ],
                }
            )
        )
        order.button_confirm()
        return order

    def test_order_and_receive_goods(self):
        order = self._order()
        self.assertEqual(order.state, "purchase")
        picking = order.picking_ids
        picking.move_ids.quantity = 4
        picking.with_user(self.user).button_validate()
        self.assertEqual(picking.state, "done")

    def test_maintain_barcode_price_and_pricelist(self):
        template = self.product.product_tmpl_id.with_user(self.user)
        template.write({"barcode": "E2E-BARCODE-1", "list_price": 25})
        self.assertEqual(self.product.barcode, "E2E-BARCODE-1")
        pricelist = (
            self.env["product.pricelist"]
            .with_user(self.user)
            .create({"name": "Tarifa e2e"})
        )
        pricelist.write({"name": "Tarifa e2e editada"})

    def test_cost_and_vendor_price_are_visible_to_the_buyer(self):
        arch = (
            self.env["product.template"]
            .with_user(self.user)
            .get_view(view_type="form")["arch"]
        )
        self.assertIn('name="standard_price"', arch)
        self.assertIn('name="seller_ids"', arch)

    def test_all_menus_open_with_real_orders(self):
        self._order()
        self.assertEqual(self.open_all_menus(self.user), {})


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestSalesOperations(StockOperationsCase):
    """Pedidos de clientes and Comerciales."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {"name": "Cliente ventas e2e", "pos_credit_sale_enabled": True}
        )

    def _quotation(self, user):
        return (
            self.env["sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.customer.id,
                    "order_line": [
                        Command.create(
                            {"product_id": self.product.id, "product_uom_qty": 2}
                        )
                    ],
                }
            )
        )

    def test_customer_orders_profile_sells_and_confirms(self):
        user = self.make_user("group_01_gestion_de_pedidos", "e2e_orders")
        order = self._quotation(user)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(self.open_all_menus(user), {})

    def test_commercial_works_only_with_own_documents(self):
        seller_a = self.make_user("group_08_menu_de_comerciales", "e2e_seller_a")
        seller_b = self.make_user("group_08_menu_de_comerciales", "e2e_seller_b")
        order_a = self._quotation(seller_a)
        order_b = self._quotation(seller_b)
        Order = self.env["sale.order"]
        self.assertEqual(
            Order.with_user(seller_a).search([("id", "in", (order_a | order_b).ids)]),
            order_a,
        )
        partners = (
            self.env["res.partner"]
            .with_user(seller_a)
            .search([("id", "=", self.customer.id)])
        )
        self.assertTrue(partners)

    def test_commercial_creates_customer_route_and_reads_reports(self):
        seller = self.make_user("group_08_menu_de_comerciales", "e2e_seller_c")
        partner = (
            self.env["res.partner"]
            .with_user(seller)
            .create({"name": "Cliente nuevo e2e"})
        )
        route = (
            self.env["todopintura.route"]
            .with_user(seller)
            .create({"name": "Ruta e2e", "user_id": seller.id})
        )
        partner.with_user(seller).write(
            {
                "route_id": route.id,
                "visit_day_ids": [
                    Command.set(
                        self.env.ref("todopintura_user_groups.weekday_monday").ids
                    )
                ],
            }
        )
        self.assertEqual(partner.route_user_id, seller)
        self.env["sale.report"].with_user(seller).formatted_read_group(
            [], ["user_id"], ["__count"]
        )
        self.assertEqual(self.open_all_menus(seller), {})

    def test_purchase_history_button_for_the_commercial(self):
        seller = self.make_user("group_08_menu_de_comerciales", "e2e_seller_d")
        order = self._quotation(seller)
        action = order.with_user(seller).action_open_purchase_history()
        self.assertEqual(action["res_model"], "sale.order.line")

    def test_direccion_reaches_everything(self):
        user = self.make_user("group_10_direccion", "e2e_direccion")
        self._quotation(user)
        self.assertEqual(self.open_all_menus(user), {})
        rate = (
            self.env["todopintura.commission.rate"]
            .with_user(user)
            .create({"user_id": user.id, "rate": 2})
        )
        self.assertTrue(rate)
