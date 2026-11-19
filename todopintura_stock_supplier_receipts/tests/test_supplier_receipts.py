# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged


class SupplierReceiptsCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env["stock.warehouse"]
        Warehouse.search([("tp_is_central_request_hub", "=", True)]).write(
            {"tp_is_central_request_hub": False}
        )
        cls.hub = Warehouse.create(
            {"name": "Central Prov", "code": "CPV", "tp_is_central_request_hub": True}
        )
        cls.shop = Warehouse.create({"name": "Tienda Prov", "code": "TPV9"})
        Partner = cls.env["res.partner"]
        cls.s1 = Partner.create({"name": "Proveedor Uno"})
        cls.s2 = Partner.create({"name": "Proveedor Dos"})
        Product = cls.env["product.product"]
        cls.p1 = Product.create({"name": "Prod P1", "is_storable": True, "barcode": "SRP0001"})
        cls.p2 = Product.create({"name": "Prod P2", "is_storable": True, "barcode": "SRP0002"})
        cls.p3 = Product.create({"name": "Prod P3", "is_storable": True, "barcode": "SRP0003"})
        cls.Picking = cls.env["stock.picking"]
        cls.pick_s1 = cls._receipt(cls.hub, cls.s1, [(cls.p1, 5), (cls.p2, 3)])
        cls.pick_s2 = cls._receipt(cls.hub, cls.s2, [(cls.p3, 4)])

    @classmethod
    def _receipt(cls, warehouse, partner, lines, confirm=True):
        supplier_loc = cls.env.ref("stock.stock_location_suppliers")
        picking = cls.Picking.create(
            {
                "picking_type_id": warehouse.in_type_id.id,
                "partner_id": partner.id,
                "location_id": supplier_loc.id,
                "location_dest_id": warehouse.lot_stock_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "location_id": supplier_loc.id,
                            "location_dest_id": warehouse.lot_stock_id.id,
                        }
                    )
                    for product, qty in lines
                ],
            }
        )
        if confirm:
            picking.action_confirm()
        return picking

    def _data(self, supplier):
        return self.Picking.with_context(tp_supplier_id=supplier.id).action_xt_get_aggregated_barcode_data(
            self.hub.lot_stock_id.id
        )

    def _scan(self, supplier, barcode, force=False):
        return self.Picking.with_context(
            tp_supplier_id=supplier.id
        ).action_xt_process_aggregated_barcode_scan(self.hub.lot_stock_id.id, barcode, force)


@tagged("post_install", "-at_install")
class TestSupplierReceipts(SupplierReceiptsCase):
    def test_pending_suppliers_and_pickings(self):
        self.assertEqual(
            self.Picking._tp_sr_pending_suppliers(), self.s1 | self.s2
        )
        self.assertEqual(self.Picking._tp_sr_pickings(self.s1), self.pick_s1)
        self.assertEqual(self.Picking._tp_sr_pickings(self.s2), self.pick_s2)

    def test_only_pending_receipts_of_the_hub_count(self):
        draft = self._receipt(self.hub, self.s1, [(self.p3, 1)], confirm=False)
        other_warehouse = self._receipt(self.shop, self.s1, [(self.p3, 1)])
        done = self._receipt(self.hub, self.s1, [(self.p3, 1)])
        for move in done.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        done.button_validate()
        pickings = self.Picking._tp_sr_pickings(self.s1)
        self.assertEqual(pickings, self.pick_s1)
        self.assertNotIn(draft, pickings)
        self.assertNotIn(other_warehouse, pickings)
        self.assertNotIn(done, pickings)

    def test_screen_shows_only_the_lines_of_that_supplier(self):
        data = self._data(self.s1)
        self.assertEqual({l["product_id"] for l in data["lines"]}, {self.p1.id, self.p2.id})
        self.assertEqual(
            {l["qty_demand"] for l in data["lines"]}, {5, 3}
        )
        self.assertEqual(data["tp_supplier_banner"]["pickings"], [self.pick_s1.name])
        self.assertEqual(data["tp_supplier_banner"]["lines"], 2)
        data2 = self._data(self.s2)
        self.assertEqual({l["product_id"] for l in data2["lines"]}, {self.p3.id})

    def test_lines_of_the_same_product_are_added_up(self):
        self._receipt(self.hub, self.s1, [(self.p1, 2)])
        data = self._data(self.s1)
        line = next(l for l in data["lines"] if l["product_id"] == self.p1.id)
        self.assertEqual(line["qty_demand"], 7)
        self.assertEqual(len(line["move_ids"]), 2)

    def test_scanning_a_product_of_the_supplier_counts_it(self):
        result = self._scan(self.s1, "SRP0001")
        self.assertTrue(result["success"], result)
        self.assertNotIn("mínimos", result["message"])
        line = next(l for l in self._data(self.s1)["lines"] if l["product_id"] == self.p1.id)
        self.assertEqual(line["qty_done"], 1)

    def test_scanning_a_product_of_another_supplier_is_rejected_and_not_added(self):
        result = self._scan(self.s1, "SRP0003")  # pertenece al proveedor Dos
        self.assertFalse(result["success"])
        self.assertIn("Proveedor Uno", result["error"])
        self.assertEqual(
            {l["product_id"] for l in self._data(self.s1)["lines"]},
            {self.p1.id, self.p2.id},
        )

    def test_unknown_barcode_is_rejected(self):
        self.assertFalse(self._scan(self.s1, "NOEXISTE")["success"])

    def test_excess_asks_for_confirmation(self):
        for _i in range(3):
            self._scan(self.s1, "SRP0002")  # demanda 3
        result = self._scan(self.s1, "SRP0002")
        self.assertEqual(result.get("type"), "excess_confirmation")
        forced = self._scan(self.s1, "SRP0002", force=True)
        self.assertTrue(forced["success"], forced)

    def test_validation_only_touches_the_scanned_pickings_of_the_supplier(self):
        for _i in range(5):
            self._scan(self.s1, "SRP0001")
        for _i in range(3):
            self._scan(self.s1, "SRP0002")
        action = self.Picking.with_context(
            tp_supplier_id=self.s1.id
        ).action_xt_validate_aggregated_pickings(self.hub.lot_stock_id.id)
        self.assertEqual(action["res_model"], "stock.picking")
        self.assertEqual(self.pick_s1.state, "done")
        self.assertNotEqual(self.pick_s2.state, "done")

    def test_validation_without_scans_returns_an_error(self):
        result = self.Picking.with_context(
            tp_supplier_id=self.s1.id
        ).action_xt_validate_aggregated_pickings(self.hub.lot_stock_id.id)
        self.assertFalse(result["success"])

    def test_without_supplier_the_original_behaviour_is_kept(self):
        data = self.Picking.action_xt_get_aggregated_barcode_data(self.hub.lot_stock_id.id)
        self.assertNotIn("tp_supplier_banner", data)
        self.assertEqual(data["picking_type_code"], "internal")

    # ---- asistente --------------------------------------------------------------------
    def test_wizard_offers_only_suppliers_with_pending_receipts(self):
        idle = self.env["res.partner"].create({"name": "Proveedor Sin Entradas"})
        wizard = self.env["stock.barcode.supplier.wizard"].create({"partner_id": self.s1.id})
        self.assertEqual(wizard.available_partner_ids, self.s1 | self.s2)
        self.assertNotIn(idle, wizard.available_partner_ids)
        self.assertEqual(wizard.pending_count, 1)

    def test_wizard_opens_the_pda_in_supplier_mode(self):
        wizard = self.env["stock.barcode.supplier.wizard"].create({"partner_id": self.s1.id})
        action = wizard.action_continue()
        self.assertEqual(action["tag"], "xtendoo_stock_barcode_client_action")
        params = action["params"]
        self.assertEqual(params["mode"], "aggregated")
        self.assertEqual(params["partner_id"], self.s1.id)
        self.assertEqual(params["location_id"], self.hub.lot_stock_id.id)

    def test_wizard_without_central_warehouse_fails(self):
        wizard = self.env["stock.barcode.supplier.wizard"].create({"partner_id": self.s1.id})
        self.hub.tp_is_central_request_hub = False
        with self.assertRaises(UserError):
            wizard.action_continue()

    def test_wizard_form_warns_when_there_are_no_pending_receipts(self):
        arch = self.env["stock.barcode.supplier.wizard"].get_view(
            self.env.ref(
                "todopintura_stock_supplier_receipts.view_stock_barcode_supplier_wizard_form"
            ).id,
            "form",
        )["arch"]
        self.assertIn("No hay recepciones de proveedor pendientes", arch)

    def test_wizard_can_open_the_classic_list(self):
        wizard = self.env["stock.barcode.supplier.wizard"].create({"partner_id": self.s1.id})
        action = wizard.action_open_list()
        self.assertEqual(action["tag"], "xtendoo_stock_barcode_picking_list")


@tagged("post_install", "-at_install")
class TestSupplierReceiptsTour(SupplierReceiptsCase, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Almacenero tour entradas",
                    "login": "almacenero_tour_entradas",
                    "password": "almacenero_tour_entradas",
                    "group_ids": [
                        Command.set(
                            [
                                cls.env.ref("base.group_user").id,
                                cls.env.ref("stock.group_stock_manager").id,
                            ]
                        )
                    ],
                }
            )
        )

    def test_entradas_button_asks_for_the_supplier(self):
        self.start_tour(
            "/odoo/action-xtendoo_stock_barcode.action_xtendoo_stock_barcode_main_menu",
            "todopintura_supplier_receipts_main_menu",
            login=self.user.login,
        )

    def test_pda_shows_only_the_supplier_lines(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Entradas tour",
                "res_model": "stock.barcode.supplier.wizard",
                "view_mode": "form",
                "target": "new",
                "context": str({"default_partner_id": self.s1.id}),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}",
            "todopintura_supplier_receipts_pda",
            login=self.user.login,
        )
