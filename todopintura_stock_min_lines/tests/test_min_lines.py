# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.tests import HttpCase, TransactionCase, tagged


class MinLinesCase(TransactionCase):
    """Datos comunes: central, tienda, productos con mínimo y stock."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env["stock.warehouse"]
        # En una BD con almacén central propio, el de la prueba debe ser el único.
        Warehouse.search([("tp_is_central_request_hub", "=", True)]).write(
            {"tp_is_central_request_hub": False}
        )
        cls.hub = Warehouse.create(
            {"name": "Central Min", "code": "CMN", "tp_is_central_request_hub": True}
        )
        cls.shop = Warehouse.create({"name": "Tienda Min", "code": "TMN"})
        Product = cls.env["product.product"]
        cls.prod_a = Product.create(
            {"name": "Prod A", "is_storable": True, "barcode": "TPMIN0001"}
        )
        cls.prod_b = Product.create(
            {"name": "Prod B", "is_storable": True, "barcode": "TPMIN0002"}
        )
        cls.prod_c = Product.create(
            {"name": "Prod C", "is_storable": True, "barcode": "TPMIN0003"}
        )
        cls.prod_free = Product.create(
            {"name": "Prod libre", "is_storable": True, "barcode": "TPMIN0009"}
        )
        Orderpoint = cls.env["stock.warehouse.orderpoint"]
        for product, minimum in ((cls.prod_a, 5), (cls.prod_b, 2), (cls.prod_c, 4)):
            Orderpoint.create(
                {
                    "product_id": product.id,
                    "warehouse_id": cls.shop.id,
                    "location_id": cls.shop.lot_stock_id.id,
                    "product_min_qty": minimum,
                    "product_max_qty": minimum,
                }
            )
        cls._stock(cls.shop, cls.prod_a, 1)  # bajo mínimo: faltan 4
        cls._stock(cls.shop, cls.prod_b, 3)  # por encima
        # prod_c sin existencias en tienda → bajo mínimo (faltan 4)
        cls._stock(cls.hub, cls.prod_a, 20)
        cls._stock(cls.hub, cls.prod_c, 0)  # sin stock en central
        cls.Picking = cls.env["stock.picking"]

    @classmethod
    def _stock(cls, warehouse, product, qty):
        if qty:
            cls.env["stock.quant"]._update_available_quantity(
                product, warehouse.lot_stock_id, qty
            )

    def _moves(self, picking):
        return picking.move_ids.filtered(lambda m: m.state != "cancel")

    def _pending_with(self, product, qty=1):
        picking = self.Picking.create(
            {
                "picking_type_id": self.hub.int_type_id.id,
                "location_id": self.hub.lot_stock_id.id,
                "location_dest_id": self.shop.lot_stock_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "location_id": self.hub.lot_stock_id.id,
                            "location_dest_id": self.shop.lot_stock_id.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        return picking


@tagged("post_install", "-at_install")
class TestMinLines(MinLinesCase):
    # ---- detección ---------------------------------------------------------------
    def test_below_min_products_and_info(self):
        below = self.shop._tp_min_below_min_products()
        self.assertEqual(below, self.prod_a | self.prod_c)
        info = self.shop._tp_min_info(self.prod_a | self.prod_b)
        self.assertEqual(info[self.prod_a.id]["on_hand"], 1)
        self.assertEqual(info[self.prod_a.id]["min"], 5)
        self.assertEqual(info[self.prod_a.id]["to_send"], 4)
        self.assertEqual(info[self.prod_b.id]["to_send"], 0)
        self.assertFalse(info[self.prod_b.id]["below_min"])

    # ---- carga de líneas ---------------------------------------------------------
    def test_load_creates_the_replenishment_with_only_below_min_lines(self):
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        picking = self.Picking.browse(summary["picking_id"])
        self.assertTrue(picking.tp_min_replenish)
        self.assertEqual(picking.location_id, self.hub.lot_stock_id)
        self.assertEqual(picking.location_dest_id, self.shop.lot_stock_id)
        moves = self._moves(picking)
        self.assertEqual(moves.product_id, self.prod_a)
        self.assertEqual(moves.product_uom_qty, 4)
        # prod_c está bajo mínimos pero no hay stock en central: no se carga
        self.assertEqual(summary["loaded"], 1)
        self.assertEqual(summary["skipped_no_stock"], 1)

    def test_quantity_is_capped_by_the_stock_available_in_central(self):
        self._stock(self.hub, self.prod_c, 3)  # faltan 4, solo hay 3
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        moves = self._moves(self.Picking.browse(summary["picking_id"]))
        self.assertEqual(
            {m.product_id: m.product_uom_qty for m in moves},
            {self.prod_a: 4, self.prod_c: 3},
        )

    def test_loading_twice_reuses_the_picking_and_does_not_duplicate(self):
        first = self.Picking.tp_load_below_min_lines(self.shop.id)
        second = self.Picking.tp_load_below_min_lines(self.shop.id)
        self.assertEqual(first["picking_id"], second["picking_id"])
        picking = self.Picking.browse(first["picking_id"])
        self.assertEqual(len(self._moves(picking)), 1)
        self.assertEqual(self._moves(picking).product_uom_qty, 4)

    def test_quantity_on_its_way_is_not_requested_again(self):
        other = self.Picking.create(
            {
                "picking_type_id": self.hub.int_type_id.id,
                "location_id": self.hub.lot_stock_id.id,
                "location_dest_id": self.shop.lot_stock_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.prod_a.id,
                            "product_uom_qty": 3,
                            "location_id": self.hub.lot_stock_id.id,
                            "location_dest_id": self.shop.lot_stock_id.id,
                        }
                    )
                ],
            }
        )
        other.action_confirm()
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        moves = self._moves(self.Picking.browse(summary["picking_id"]))
        self.assertEqual(moves.product_uom_qty, 1)  # 5 − 1 existencias − 3 en camino

    def test_refresh_adds_adjusts_and_removes_lines(self):
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        picking = self.Picking.browse(summary["picking_id"])
        # la tienda recibe stock de A (ya no está bajo mínimos) y C llega a central
        self._stock(self.shop, self.prod_a, 10)
        self._stock(self.hub, self.prod_c, 10)
        self.Picking.tp_load_below_min_lines(self.shop.id)
        moves = self._moves(picking)
        self.assertEqual(moves.product_id, self.prod_c)
        self.assertEqual(moves.product_uom_qty, 4)

    def test_scanned_lines_are_kept_on_refresh(self):
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        picking = self.Picking.browse(summary["picking_id"])
        move = self._moves(picking)
        picking.sudo().action_xt_complete_line(move.id)
        self.assertTrue(move.xt_barcode_scanned_qty)
        self._stock(self.shop, self.prod_a, 10)  # ya no está bajo mínimos
        self.Picking.tp_load_below_min_lines(self.shop.id)
        self.assertEqual(self._moves(picking).product_id, self.prod_a)

    def test_central_warehouse_has_no_replenishment(self):
        summary = self.Picking.tp_load_below_min_lines(self.hub.id)
        self.assertFalse(summary["picking_id"])

    def test_nothing_below_min_creates_nothing(self):
        self._stock(self.shop, self.prod_a, 10)
        self._stock(self.shop, self.prod_c, 10)
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        self.assertFalse(summary["picking_id"])
        self.assertEqual(summary["loaded"], 0)

    # ---- pantalla PDA y formulario ---------------------------------------------------
    def test_pda_lines_carry_stock_min_and_quantity_to_send(self):
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        picking = self.Picking.browse(summary["picking_id"])
        data = self.Picking.action_xt_get_aggregated_barcode_data(
            self.shop.lot_stock_id.id
        )
        line = next(l for l in data["lines"] if l["product_id"] == self.prod_a.id)
        self.assertEqual(line["tp_dest_qty"], 1)
        self.assertEqual(line["tp_min_qty"], 5)
        self.assertEqual(line["tp_to_send"], 4)
        self.assertTrue(line["tp_below_min"])
        banner = data["tp_banner"]
        self.assertEqual(banner["below_min"], 2)
        self.assertEqual(banner["loaded"], 1)
        self.assertEqual(banner["on_screen"], 1)
        self.assertEqual(banner["hidden"], 0)
        self.assertEqual(banner["skipped_no_stock"], 1)  # prod_c sin stock en central
        self.assertEqual(banner["picking"], picking.name)
        single = picking.action_xt_get_barcode_data()
        self.assertEqual(single["lines"][0]["tp_min_qty"], 5)
        self.assertTrue(single["tp_banner"])

    def test_banner_counts_lines_on_screen_and_the_hidden_ones(self):
        """Una línea de un traslado pendiente que NO está bajo mínimos queda oculta."""
        self._pending_with(self.prod_b)  # prod_b tiene 3 ≥ mínimo 2
        self.Picking.tp_load_below_min_lines(self.shop.id)
        data = self.Picking.action_xt_get_aggregated_barcode_data(
            self.shop.lot_stock_id.id
        )
        banner = data["tp_banner"]
        self.assertEqual(banner["on_screen"], 1)  # prod_a
        self.assertEqual(banner["hidden"], 1)  # prod_b
        flags = {l["product_id"]: l["tp_below_min"] for l in data["lines"]}
        self.assertTrue(flags[self.prod_a.id])
        self.assertFalse(flags[self.prod_b.id])

    def test_scanning_a_product_not_below_min_warns_but_adds_it(self):
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        picking = self.Picking.browse(summary["picking_id"])
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": self.prod_free.id,
                "product_uom_qty": 2,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
            }
        )
        self._stock(self.hub, self.prod_free, 5)
        picking.action_assign()
        result = self.Picking.action_xt_process_aggregated_barcode_scan(
            self.shop.lot_stock_id.id, "TPMIN0009"
        )
        self.assertTrue(result["success"], result)
        self.assertIn("No está bajo mínimos", result["message"])
        self.assertTrue(result["excess"])

    def test_scanning_a_below_min_product_has_no_warning(self):
        self.Picking.tp_load_below_min_lines(self.shop.id)
        result = self.Picking.action_xt_process_aggregated_barcode_scan(
            self.shop.lot_stock_id.id, "TPMIN0001"
        )
        self.assertTrue(result["success"], result)
        self.assertNotIn("No está bajo mínimos", result["message"])

    def test_move_columns_follow_the_destination_warehouse(self):
        summary = self.Picking.tp_load_below_min_lines(self.shop.id)
        move = self._moves(self.Picking.browse(summary["picking_id"]))
        self.assertEqual((move.tp_dest_qty, move.tp_min_qty, move.tp_to_send), (1, 5, 4))

    def test_form_shows_the_columns(self):
        arch = self.Picking.get_view(self.env.ref("stock.view_picking_form").id, "form")[
            "arch"
        ]
        for name in ("tp_dest_qty", "tp_min_qty", "tp_to_send"):
            self.assertIn(name, arch)

    # ---- asistente «Seleccionar almacén» ---------------------------------------------
    def test_wizard_loads_the_lines_before_opening_the_pda(self):
        wizard = self.env["stock.barcode.internal.wizard"].create(
            {"warehouse_id": self.shop.id}
        )
        action = wizard.action_continue()
        self.assertEqual(action["tag"], "xtendoo_stock_barcode_client_action")
        self.assertEqual(action["params"]["warehouse_id"], self.shop.id)
        picking = self.Picking.search(
            [
                ("tp_min_replenish", "=", True),
                ("location_dest_id", "=", self.shop.lot_stock_id.id),
            ]
        )
        self.assertEqual(self._moves(picking).product_id, self.prod_a)


@tagged("post_install", "-at_install")
class TestMinLinesTour(MinLinesCase, HttpCase):
    """En el navegador: asistente de almacén → PDA con aviso y datos por línea."""

    def test_wizard_opens_the_pda_with_the_below_min_lines(self):
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Almacenero tour mínimos",
                    "login": "almacenero_tour_min",
                    "password": "almacenero_tour_min",
                    "group_ids": [
                        Command.set(
                            [
                                self.env.ref("base.group_user").id,
                                self.env.ref("stock.group_stock_manager").id,
                            ]
                        )
                    ],
                }
            )
        )
        self._pending_with(self.prod_b)
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Seleccionar almacén tour",
                "res_model": "stock.barcode.internal.wizard",
                "view_mode": "form",
                "target": "new",
                "context": str({"default_warehouse_id": self.shop.id}),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}",
            "todopintura_stock_min_lines_pda",
            login=user.login,
        )
        picking = self.env["stock.picking"].search(
            [("tp_min_replenish", "=", True), ("location_dest_id", "=", self.shop.lot_stock_id.id)]
        )
        self.assertEqual(self._moves(picking).product_id, self.prod_a)
