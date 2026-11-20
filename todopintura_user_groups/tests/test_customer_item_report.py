# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import io
import zipfile

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, tagged

from .common import TodopinturaTestCase

MODULE = "todopintura_user_groups"


class CustomerItemReportCase(TodopinturaTestCase):
    """Datos comunes: dos clientes, dos artículos con proveedor y varios pedidos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env["stock.warehouse"]
        cls.wh1 = Warehouse.create({"name": "Tienda CIR 1", "code": "CI1"})
        cls.wh2 = Warehouse.create({"name": "Tienda CIR 2", "code": "CI2"})
        Partner = cls.env["res.partner"]
        cls.alfa = Partner.create({"name": "Cliente Alfa CIR", "ref": "C-ALFA"})
        cls.alfa_contact = Partner.create(
            {"name": "Contacto Alfa", "parent_id": cls.alfa.id}
        )
        cls.beta = Partner.create({"name": "Cliente Beta CIR", "ref": "C-BETA"})
        cls.sup1 = Partner.create({"name": "Proveedor CIR 1", "supplier_rank": 1})
        cls.sup2 = Partner.create({"name": "Proveedor CIR 2", "supplier_rank": 1})
        Product = cls.env["product.product"]
        cls.prod_a = Product.create(
            {"name": "Articulo A CIR", "default_code": "CIR-A", "standard_price": 6.0}
        )
        cls.prod_b = Product.create(
            {"name": "Articulo B CIR", "default_code": "CIR-B", "standard_price": 2.0}
        )
        for product, supplier in ((cls.prod_a, cls.sup1), (cls.prod_b, cls.sup2)):
            cls.env["product.supplierinfo"].create(
                {
                    "partner_id": supplier.id,
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "price": 1.0,
                }
            )
        cls.so1 = cls._sale(cls.alfa, cls.wh1, [(cls.prod_a, 3, 10.0), (cls.prod_b, 2, 5.0)])
        cls.so2 = cls._sale(cls.alfa_contact, cls.wh2, [(cls.prod_a, 1, 12.0)])
        cls.so3 = cls._sale(
            cls.beta, cls.wh1, [(cls.prod_b, 4, 5.0)], date="2020-01-15 10:00:00"
        )
        cls.draft = cls.env["sale.order"].create(
            {
                "partner_id": cls.beta.id,
                "warehouse_id": cls.wh1.id,
                "order_line": [Command.create({"product_id": cls.prod_a.id, "product_uom_qty": 99, "price_unit": 1.0})],
            }
        )

    @classmethod
    def _sale(cls, partner, warehouse, lines, date=None):
        order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [
                    Command.create(
                        {"product_id": product.id, "product_uom_qty": qty, "price_unit": price}
                    )
                    for product, qty, price in lines
                ],
            }
        )
        order.action_confirm()
        if date:
            order.date_order = date
        return order

    def _wizard(self, **values):
        defaults = {
            "date_from": "2000-01-01",
            "date_to": fields.Date.today(),
            "warehouse_ids": [Command.set((self.wh1 | self.wh2).ids)],
        }
        return self.env["todopintura.customer.item.report"].create({**defaults, **values})

    def _rows(self, wizard=None, **values):
        wizard = wizard or self._wizard(**values)
        return wizard._get_rows()



@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestCustomerItemReport(CustomerItemReportCase):
    """Listado acumulado de artículos por cliente."""

    # ---- estructura y cifras ---------------------------------------------------------
    def test_rows_group_articles_under_each_customer_with_their_totals(self):
        rows = self._rows()
        kinds = [r["kind"] for r in rows]
        self.assertEqual(kinds, ["customer", "item", "item", "customer", "item", "total"])
        alfa, a, b, beta, beta_b, total = rows
        # Cliente Alfa: sus pedidos + los de su contacto, agrupados en la empresa
        self.assertEqual((alfa["code"], alfa["name"]), ("C-ALFA", "Cliente Alfa CIR"))
        self.assertEqual(alfa["qty"], 6)
        self.assertAlmostEqual(alfa["total_sale"], 52.0)
        self.assertAlmostEqual(alfa["total_cost"], 28.0)
        self.assertAlmostEqual(alfa["total_margin"], 24.0)
        self.assertAlmostEqual(alfa["margin_percent"], 24.0 / 52.0 * 100)
        # Artículo A: 4 uds a 42 € de venta y 24 € de coste → por unidad 10,5 / 6 / 4,5
        self.assertEqual((a["code"], a["name"]), ("CIR-A", "Articulo A CIR"))
        self.assertEqual(a["qty"], 4)
        self.assertAlmostEqual(a["price_unit"], 10.5)
        self.assertAlmostEqual(a["cost_unit"], 6.0)
        self.assertAlmostEqual(a["margin_unit"], 4.5)
        self.assertAlmostEqual(a["total_sale"], 42.0)
        self.assertAlmostEqual(a["total_cost"], 24.0)
        self.assertAlmostEqual(a["total_margin"], 18.0)
        self.assertAlmostEqual(a["margin_percent"], 18.0 / 42.0 * 100)
        self.assertEqual((b["qty"], b["total_sale"], b["total_cost"]), (2, 10.0, 4.0))
        # El cliente no muestra precios por unidad
        self.assertEqual((alfa["price_unit"], alfa["cost_unit"], alfa["margin_unit"]), (0, 0, 0))
        self.assertEqual(beta["name"], "Cliente Beta CIR")
        self.assertEqual(beta_b["qty"], 4)
        # Total general
        self.assertEqual(total["name"], "TOTAL")
        self.assertAlmostEqual(total["total_sale"], 72.0)
        self.assertAlmostEqual(total["total_cost"], 36.0)
        self.assertAlmostEqual(total["total_margin"], 36.0)
        self.assertAlmostEqual(total["margin_percent"], 50.0)

    def test_draft_quotations_are_not_counted(self):
        names = [r["name"] for r in self._rows() if r["kind"] == "item"]
        self.assertEqual(names.count("Articulo A CIR"), 1)  # solo el de Alfa, no los 99 del borrador

    def test_filter_by_customer(self):
        rows = self._rows(partner_ids=[Command.set(self.beta.ids)])
        self.assertEqual([r["name"] for r in rows if r["kind"] == "customer"], ["Cliente Beta CIR"])

    def test_filter_by_customer_includes_its_contacts(self):
        rows = self._rows(partner_ids=[Command.set(self.alfa.ids)])
        alfa = next(r for r in rows if r["kind"] == "customer")
        self.assertAlmostEqual(alfa["total_sale"], 52.0)

    def test_filter_by_supplier_keeps_only_their_articles(self):
        rows = self._rows(supplier_ids=[Command.set(self.sup1.ids)])
        items = [r["name"] for r in rows if r["kind"] == "item"]
        self.assertEqual(items, ["Articulo A CIR"])
        rows = self._rows(supplier_ids=[Command.set((self.sup1 | self.sup2).ids)])
        self.assertEqual(len([r for r in rows if r["kind"] == "item"]), 3)

    def test_filter_by_dates(self):
        rows = self._rows(date_from="2019-12-01", date_to="2020-02-01")
        self.assertEqual([r["name"] for r in rows if r["kind"] == "customer"], ["Cliente Beta CIR"])
        self.assertEqual(self._rows(date_from="1999-01-01", date_to="1999-12-31"), [])

    def test_filter_by_warehouse(self):
        rows = self._rows(warehouse_ids=[Command.set(self.wh2.ids)])
        alfa = next(r for r in rows if r["kind"] == "customer")
        self.assertAlmostEqual(alfa["total_sale"], 12.0)  # solo el pedido del contacto en wh2
        self.assertEqual(len([r for r in rows if r["kind"] == "customer"]), 1)

    def test_users_with_assigned_warehouses_only_see_their_own(self):
        store = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Tienda CIR",
                    "login": "tienda_cir",
                    "group_ids": [Command.set(self.env.ref(f"{MODULE}.perm_va14_items").ids)],
                    "allowed_warehouse_ids": [Command.set(self.wh2.ids)],
                }
            )
        )
        wizard = self._wizard().with_user(store)
        rows = wizard._get_rows()
        self.assertAlmostEqual(
            next(r for r in rows if r["kind"] == "total")["total_sale"], 12.0
        )

    def test_dates_are_validated(self):
        with self.assertRaises(ValidationError):
            self._wizard(date_from="2026-02-01", date_to="2026-01-01")

    # ---- listado y exportación ------------------------------------------------------------
    def test_show_creates_the_list(self):
        wizard = self._wizard()
        action = wizard.action_show()
        self.assertEqual(action["res_model"], "todopintura.customer.item.report.line")
        self.assertEqual(action["domain"], [("report_id", "=", wizard.id)])
        # Agrupado por clientes por defecto; las líneas son solo de artículos
        self.assertEqual(action["context"]["group_by"], ["customer_label"])
        lines = self.env["todopintura.customer.item.report.line"].search(action["domain"])
        self.assertEqual(len(lines), 3)
        self.assertEqual(set(lines.mapped("kind")), {"item"})
        self.assertEqual(
            sorted(set(lines.mapped("customer_label"))),
            ["Cliente Alfa CIR (C-ALFA)", "Cliente Beta CIR (C-BETA)"],
        )
        # Volver a ver el listado lo recalcula sin duplicar
        wizard.action_show()
        self.assertEqual(
            self.env["todopintura.customer.item.report.line"].search_count(action["domain"]), 3
        )

    def test_customer_group_header_has_weighted_totals_and_margin_percent(self):
        """Cabecera de cada cliente: sumas y % de margen = margen / venta (no suma de %)."""
        _plain, with_cost = self._users()
        wizard = self._wizard()
        wizard.with_user(with_cost).action_show()
        Line = self.env["todopintura.customer.item.report.line"].with_user(with_cost)
        groups = Line.formatted_read_group(
            [("report_id", "=", wizard.id)],
            ["customer_label"],
            ["qty:sum", "total_sale:sum", "total_cost:sum", "total_margin:sum", "margin_percent:sum"],
            order="customer_label",
        )
        alfa = next(g for g in groups if g["customer_label"].startswith("Cliente Alfa"))
        self.assertAlmostEqual(alfa["qty:sum"], 6)
        self.assertAlmostEqual(alfa["total_sale:sum"], 52.0)
        self.assertAlmostEqual(alfa["total_cost:sum"], 28.0)
        self.assertAlmostEqual(alfa["total_margin:sum"], 24.0)
        self.assertAlmostEqual(alfa["margin_percent:sum"], 24.0 / 52.0 * 100)
        # y no la suma de los % de sus artículos (42,9 % + 60 % = 102,9 %)
        self.assertLess(alfa["margin_percent:sum"], 100)

    def test_unit_values_are_not_added_up_in_the_customer_header(self):
        """Precio venta/costo y margen son «por unidad»: no tienen suma de grupo."""
        Line = self.env["todopintura.customer.item.report.line"]
        for name in ("price_unit", "cost_unit", "margin_unit"):
            self.assertFalse(Line._fields[name].aggregator, name)
        for name in ("qty", "total_sale", "total_cost", "total_margin"):
            self.assertEqual(Line._fields[name].aggregator, "sum", name)

    def _view_arch(self, user):
        return self.env["todopintura.customer.item.report.line"].with_user(user).get_view(
            self.env.ref(f"{MODULE}.view_customer_item_report_line_list").id, "list"
        )["arch"]

    def test_list_view_has_the_requested_columns(self):
        plain, with_cost = self._users()
        arch = self._view_arch(with_cost)
        for name in (
            "code", "name", "qty", "price_unit", "cost_unit", "margin_unit",
            "total_sale", "total_cost", "total_margin", "margin_percent",
        ):
            self.assertIn(f'name="{name}"', arch)
        # Sin el grupo de costes, la lista no trae costes ni márgenes
        arch = self._view_arch(plain)
        for name in ("code", "name", "qty", "price_unit", "total_sale"):
            self.assertIn(f'name="{name}"', arch)
        for name in ("cost_unit", "margin_unit", "total_cost", "total_margin", "margin_percent"):
            self.assertNotIn(f'name="{name}"', arch)

    def _users(self):
        Users = self.env["res.users"].with_context(no_reset_password=True)
        perm = self.env.ref(f"{MODULE}.perm_va14_items")
        cost = self.env.ref(f"{MODULE}.group_cost_viewer")
        plain = Users.create(
            {"name": "Sin costes", "login": "cir_plain", "group_ids": [Command.set(perm.ids)]}
        )
        with_cost = Users.create(
            {"name": "Con costes", "login": "cir_cost", "group_ids": [Command.set((perm | cost).ids)]}
        )
        return plain, with_cost

    def test_cost_and_margin_are_hidden_without_the_cost_group(self):
        plain, with_cost = self._users()
        wizard = self._wizard()
        wizard.with_user(plain).action_show()
        line = self.env["todopintura.customer.item.report.line"].with_user(plain).search(
            [("report_id", "=", wizard.id)], limit=1
        )
        self.assertTrue(line.total_sale >= 0)  # las ventas sí se ven
        for field in ("total_cost", "total_margin", "margin_percent", "cost_unit", "margin_unit"):
            with self.assertRaises(AccessError, msg=field):
                line.mapped(field)
        # Quien tiene el grupo de costes los ve
        line_cost = self.env["todopintura.customer.item.report.line"].with_user(with_cost).search(
            [("report_id", "=", wizard.id)], order="sequence", limit=1
        )
        self.assertEqual(line_cost.code, "CIR-A")
        self.assertAlmostEqual(line_cost.total_cost, 24.0)

    def _xlsx_strings(self, action, user):
        attachment = self.env["ir.attachment"].browse(
            int(action["url"].split("/web/content/")[1].split("?")[0])
        )
        with zipfile.ZipFile(io.BytesIO(attachment.raw)) as book:
            return book.read("xl/sharedStrings.xml").decode()

    def test_excel_export_has_every_column_for_the_cost_viewer(self):
        _plain, with_cost = self._users()
        action = self._wizard().with_user(with_cost).action_export_xlsx()
        self.assertTrue(action["url"].startswith("/web/content/"))
        strings = self._xlsx_strings(action, with_cost)
        for text in (
            "Código", "Descripción", "Cantidad", "Precio venta", "Precio costo",
            "Margen", "T. Venta", "T. Costo", "T. Margen", "% Margen",
            "Cliente Alfa CIR", "Articulo A CIR", "TOTAL",
        ):
            self.assertIn(text, strings)

    def test_excel_export_has_no_cost_columns_without_the_cost_group(self):
        plain, _with_cost = self._users()
        action = self._wizard().with_user(plain).action_export_xlsx()
        strings = self._xlsx_strings(action, plain)
        self.assertIn("T. Venta", strings)
        for text in ("Precio costo", "T. Costo", "T. Margen", "% Margen"):
            self.assertNotIn(text, strings)

    # ---- menú ---------------------------------------------------------------------------------
    def test_menu_and_permission_exist(self):
        menu = self.env.ref(f"{MODULE}.menu_vt_customer_items")
        self.assertEqual(menu.name, "Listado acumulado de artículos por cliente")
        self.assertEqual(menu.parent_id, self.env.ref(f"{MODULE}.menu_vt_lists_group"))
        self.assertIn(
            self.env.ref(f"{MODULE}.perm_va14_items"),
            self.env.ref(f"{MODULE}.group_06_ventas_de_tiendas").implied_ids,
        )



@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestCustomerItemReportTour(CustomerItemReportCase, HttpCase):
    """En el navegador: asistente → listado en modo lista, solo lectura."""

    def test_wizard_opens_the_list(self):
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Listado tour",
                    "login": "listado_tour_cir",
                    "password": "listado_tour_cir",
                    "group_ids": [
                        Command.set(
                            [
                                self.env.ref("base.group_user").id,
                                self.env.ref(f"{MODULE}.perm_va14_items").id,
                                self.env.ref(f"{MODULE}.group_cost_viewer").id,
                            ]
                        )
                    ],
                }
            )
        )
        self.start_tour(
            f"/odoo/action-{MODULE}.action_customer_item_report",
            "todopintura_customer_item_report_list",
            login=user.login,
        )
