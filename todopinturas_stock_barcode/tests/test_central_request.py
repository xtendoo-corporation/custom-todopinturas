from odoo.tests.common import TransactionCase


class TestTodopinturasCentralRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.central_warehouse = cls.env["stock.warehouse"].search([
            ("company_id", "=", cls.company.id),
        ], limit=1)
        cls.central_warehouse.tp_is_central_request_hub = True
        cls.store_location_1 = cls.env["stock.location"].create({
            "name": "Tienda Norte",
            "location_id": cls.central_warehouse.lot_stock_id.id,
            "usage": "internal",
        })
        cls.store_location_2 = cls.env["stock.location"].create({
            "name": "Tienda Sur",
            "location_id": cls.central_warehouse.lot_stock_id.id,
            "usage": "internal",
        })

    def _set_warehouse_name(self, warehouse, name):
        self.env.cr.execute(
            "UPDATE stock_warehouse SET name = %s WHERE id = %s",
            [name, warehouse.id],
        )
        warehouse.invalidate_recordset(["name"])

    def _create_internal_picking(self, source_location, destination_location):
        return self.env["stock.picking"].create({
            "picking_type_id": self.central_warehouse.int_type_id.id,
            "location_id": source_location.id,
            "location_dest_id": destination_location.id,
        })

    def _create_outgoing_picking(self, destination_location):
        customer_location = self.env.ref("stock.stock_location_customers")
        return self.env["stock.picking"].create({
            "picking_type_id": self.central_warehouse.out_type_id.id,
            "location_id": destination_location.id,
            "location_dest_id": customer_location.id,
        })

    def _create_central_non_customer_picking(self, destination_location):
        return self.env["stock.picking"].create({
            "picking_type_id": self.central_warehouse.out_type_id.id,
            "location_id": self.central_warehouse.lot_stock_id.id,
            "location_dest_id": destination_location.id,
        })

    def test_picking_from_central_to_non_customer_location_is_marked_as_request(self):
        picking = self._create_central_non_customer_picking(self.store_location_1)

        self.assertTrue(picking.tp_is_central_request)
        self.assertEqual(picking.tp_request_source_warehouse_id, self.central_warehouse)
        self.assertEqual(picking.tp_request_destination_warehouse_id, self.central_warehouse)

    def test_picking_from_central_to_customers_is_not_marked_as_request(self):
        picking = self._create_outgoing_picking(self.central_warehouse.lot_stock_id)

        self.assertFalse(picking.tp_is_central_request)
        self.assertEqual(picking.tp_request_source_warehouse_id, self.central_warehouse)
        self.assertFalse(picking.tp_request_destination_warehouse_id)

    def test_picking_from_named_central_warehouse_is_marked_without_flag(self):
        self.central_warehouse.tp_is_central_request_hub = False
        self._set_warehouse_name(self.central_warehouse, "Central")

        picking = self._create_central_non_customer_picking(self.store_location_1)

        self.assertTrue(picking.tp_is_central_request)
        self.assertEqual(
            self.env["stock.picking"].search([("tp_is_central_request", "=", True)]),
            picking,
        )

    def test_action_view_tp_central_requests_for_central_shows_all(self):
        picking_store_1 = self._create_central_non_customer_picking(self.store_location_1)
        picking_store_2 = self._create_central_non_customer_picking(self.store_location_2)
        self._create_outgoing_picking(self.central_warehouse.lot_stock_id)

        action = self.central_warehouse.action_view_tp_central_requests()
        visible = self.env["stock.picking"].search(action["domain"])

        self.assertEqual(visible, picking_store_1 | picking_store_2)
        self.assertFalse(action["context"]["default_location_dest_id"])

    def test_central_request_count_uses_internal_pickings_from_central(self):
        self._create_central_non_customer_picking(self.store_location_1)
        self._create_central_non_customer_picking(self.store_location_1)
        self._create_central_non_customer_picking(self.store_location_2)
        self._create_outgoing_picking(self.central_warehouse.lot_stock_id)

        self.central_warehouse.invalidate_recordset(["tp_central_request_count"])

        self.assertEqual(self.central_warehouse.tp_central_request_count, 3)

    def test_action_window_uses_stock_picking(self):
        action = self.env.ref("todopinturas_stock_barcode.action_todopinturas_central_request")

        self.assertEqual(action.res_model, "stock.picking")
        self.assertEqual(action.view_mode, "list,form")
        self.assertEqual(action.context, "{}")

    def test_action_open_tp_central_requests_for_current_user_returns_dynamic_action(self):
        result = self.env["stock.warehouse"].action_open_tp_central_requests_for_current_user()

        self.assertIn("action", result)
        self.assertEqual(result["action"]["domain"], [("tp_is_central_request", "=", True)])
        self.assertEqual(
            result["action"]["context"]["default_location_id"],
            self.central_warehouse.lot_stock_id.id,
        )

    def test_action_open_tp_central_requests_for_current_user_warns_without_central_hub(self):
        self.central_warehouse.tp_is_central_request_hub = False
        self._set_warehouse_name(self.central_warehouse, "WH")

        result = self.env["stock.warehouse"].action_open_tp_central_requests_for_current_user()

        self.assertIn("warning", result)
        self.assertIn("almacén central", result["warning"]["message"])

    def test_action_open_tp_central_requests_for_current_user_uses_named_central_fallback(self):
        self.central_warehouse.tp_is_central_request_hub = False
        self._set_warehouse_name(self.central_warehouse, "Central")

        result = self.env["stock.warehouse"].action_open_tp_central_requests_for_current_user()

        self.assertIn("action", result)
        self.assertEqual(
            result["action"]["context"]["default_location_id"],
            self.central_warehouse.lot_stock_id.id,
        )

    def test_menu_is_inside_xtendoo_barcode(self):
        menu = self.env.ref("todopinturas_stock_barcode.menu_todopinturas_stock_barcode_root")
        xt_menu = self.env.ref("xtendoo_stock_barcode.menu_xtendoo_stock_barcode_root")

        self.assertEqual(menu.parent_id, xt_menu)


