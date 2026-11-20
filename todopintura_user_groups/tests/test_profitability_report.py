# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import io
import zipfile

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import TodopinturaTestCase

MODULE = "todopintura_user_groups"
DAY = "2031-03-12"  # un día sin datos reales en la BD


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestProfitabilityReport(TodopinturaTestCase):
    """Listado de rentabilidad por línea (exportable a Excel)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env["stock.warehouse"]
        cls.wh1 = Warehouse.create({"name": "Tienda RENT 1", "code": "RN1"})
        cls.wh2 = Warehouse.create({"name": "Tienda RENT 2", "code": "RN2"})
        cls.sessions = {}
        for warehouse in (cls.wh1, cls.wh2):
            config = cls.env["pos.config"].create(
                {"name": f"TPV {warehouse.code}", "picking_type_id": warehouse.pos_type_id.id}
            )
            cls.sessions[warehouse] = cls.env["pos.session"].create({"config_id": config.id})
        cls.pricelist = cls.env["product.pricelist"].search(
            [("company_id", "in", [False, cls.env.company.id])], limit=1
        ) or cls.env["product.pricelist"].create({"name": "Tarifa RENT"})
        Partner = cls.env["res.partner"]
        cls.cliente = Partner.create({"name": "CLIENTE RENT SL", "ref": "21337"})
        Product = cls.env["product.product"]
        cls.art = Product.create(
            {"name": "Articulo Rent", "default_code": "ART-RENT", "standard_price": 6.0,
             "is_storable": False, "taxes_id": [Command.clear()]}
        )
        cls.art_edge = Product.create(
            {"name": "Articulo Limite", "default_code": "ART-EDGE", "standard_price": 7.0,
             "is_storable": False, "taxes_id": [Command.clear()]}
        )
        cls.seller = cls.env["res.users"].create({"name": "Comercial Rent", "login": "com_rent"})
        cls.env.user.tz = "Europe/Madrid"

    # ---- helpers -----------------------------------------------------------------------
    @classmethod
    def _ticket(cls, warehouse, number, qty, price, state="paid", open_picking=False, product=None):
        product = product or cls.art
        order = cls.env["pos.order"].with_context(allow_price_update=True).create(
            {
                "name": number,
                "pos_reference": number,
                "session_id": cls.sessions[warehouse].id,
                "pricelist_id": cls.pricelist.id,
                "partner_id": cls.cliente.id,
                "user_id": cls.seller.id,
                "date_order": f"{DAY} 10:00:00",
                "state": state,
                "amount_tax": 0,
                "amount_total": qty * price,
                "amount_paid": qty * price,
                "amount_return": 0,
                "lines": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "qty": qty,
                            "price_unit": price,
                            "price_subtotal": qty * price,
                            "price_subtotal_incl": qty * price,
                        }
                    )
                ],
            }
        )
        if open_picking:
            warehouse_type = warehouse.out_type_id
            cls.env["stock.picking"].create(
                {
                    "picking_type_id": warehouse_type.id,
                    "location_id": warehouse.lot_stock_id.id,
                    "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
                    "pos_order_id": order.id,
                }
            )
        return order

    @classmethod
    def _sale(cls, warehouse, qty, price, deliver=True, invoice=False):
        order = cls.env["sale.order"].create(
            {
                "partner_id": cls.cliente.id,
                "warehouse_id": warehouse.id,
                "user_id": cls.seller.id,
                "order_line": [
                    Command.create({"product_id": cls.art.id, "product_uom_qty": qty, "price_unit": price})
                ],
            }
        )
        order.action_confirm()
        if deliver:
            for picking in order.picking_ids:
                picking.move_ids.write({"quantity": qty, "picked": True})
                picking.button_validate()
            order.picking_ids.move_ids.write({"date": f"{DAY} 11:00:00"})
        if invoice:
            move = order._create_invoices()
            move.action_post()
        return order

    @classmethod
    def _invoice(cls, qty, price, move_type="out_invoice", day=DAY):
        move = cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": cls.cliente.id,
                "invoice_user_id": cls.seller.id,
                "invoice_date": day,
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": cls.art.id, "quantity": qty, "price_unit": price, "tax_ids": [Command.clear()]}
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _report(self, **values):
        defaults = {"date_from": DAY, "date_to": DAY, "warehouse_ids": [Command.set((self.wh1 | self.wh2).ids)]}
        return self.env["todopintura.profitability.report"].create({**defaults, **values})

    def _rows(self, **values):
        return self._report(**values)._get_rows()

    # ---- cifras y marca «**» ------------------------------------------------------------------
    def test_row_has_the_columns_of_the_excel_with_unit_prices_and_profit(self):
        self._ticket(self.wh1, "T-0001", 2, 10.0)
        row = self._rows()[0]
        self.assertEqual(row["warehouse_name"], "Tienda RENT 1")
        self.assertEqual(row["user_name"], "Comercial Rent")
        self.assertEqual((row["product_code"], row["product_name"]), ("ART-RENT", "Articulo Rent"))
        self.assertEqual((row["partner_code"], row["partner_name"]), ("21337", "CLIENTE RENT SL"))
        self.assertEqual(str(row["date"]), DAY)
        self.assertEqual(row["number"], "T-0001")
        self.assertEqual(row["qty"], 2)
        self.assertAlmostEqual(row["cost_unit"], 6.0)
        self.assertAlmostEqual(row["price_unit"], 10.0)
        self.assertAlmostEqual(row["profit"], 8.0)  # (10 − 6) × 2
        self.assertAlmostEqual(row["profit_percent"], 40.0)
        self.assertEqual(row["flag"], "")

    def test_amounts_are_rounded_to_two_decimals_like_the_example(self):
        self._ticket(self.wh1, "T-0003", 3, 10.0 / 3)  # 3,3333… de precio
        row = self._rows()[0]
        for field in ("cost_unit", "price_unit", "profit", "profit_percent"):
            self.assertEqual(row[field], round(row[field], 2), field)

    def test_two_asterisks_when_the_profit_is_under_30_percent(self):
        self._ticket(self.wh1, "T-LOW", 1, 7.0)  # (7−6)/7 = 14,3 %
        self._ticket(self.wh1, "T-EDGE", 1, 10.0, product=self.art_edge)  # (10−7)/10 = 30 % justo
        self._ticket(self.wh1, "T-OK", 1, 12.0)  # 50 %
        rows = {r["number"]: r for r in self._rows()}
        self.assertEqual(rows["T-LOW"]["flag"], "**")
        self.assertAlmostEqual(rows["T-LOW"]["profit_percent"], 14.29)  # redondeado a 2 decimales
        self.assertEqual(rows["T-OK"]["flag"], "")
        self.assertEqual(rows["T-EDGE"]["flag"], "")  # 30 % no es «menor de 30»

    # ---- tipo de documento ---------------------------------------------------------------------
    def test_delivered_order_without_invoice_is_an_albaran(self):
        order = self._sale(self.wh1, 3, 10.0)
        row = next(r for r in self._rows() if r["number"] == order.name)
        self.assertEqual(row["doc_type"], "ALBARAN")
        self.assertEqual(row["qty"], 3)
        self.assertAlmostEqual(row["price_unit"], 10.0)

    def test_delivered_and_invoiced_order_is_cash(self):
        order = self._sale(self.wh1, 3, 10.0, invoice=True)
        row = next(r for r in self._rows() if r["number"] == order.name)
        self.assertEqual(row["doc_type"], "Contado")

    def test_tickets_and_loose_invoices_are_cash(self):
        self._ticket(self.wh1, "T-0001", 1, 10.0)
        invoice = self._invoice(3, 10.0)
        rows = {r["number"]: r for r in self._rows(warehouse_ids=[Command.clear()])}
        self.assertEqual(rows["T-0001"]["doc_type"], "Contado")
        self.assertEqual(rows[invoice.name]["doc_type"], "Contado")
        self.assertEqual(rows[invoice.name]["qty"], 3)
        self.assertEqual(rows[invoice.name]["warehouse_name"], "")  # la factura suelta no tiene almacén

    def test_refunds_come_out_negative(self):
        refund = self._invoice(1, 10.0, move_type="out_refund")
        row = next(r for r in self._rows(warehouse_ids=[Command.clear()]) if r["number"] == refund.name)
        self.assertEqual(row["qty"], -1)
        self.assertAlmostEqual(row["profit"], -4.0)

    # ---- solo lo entregado -----------------------------------------------------------------------
    def test_only_delivered_orders_are_listed(self):
        delivered = self._sale(self.wh1, 1, 10.0)
        pending = self._sale(self.wh1, 1, 10.0, deliver=False)
        numbers = {r["number"] for r in self._rows()}
        self.assertIn(delivered.name, numbers)
        self.assertNotIn(pending.name, numbers)

    def test_tickets_with_goods_still_to_deliver_are_not_listed(self):
        self._ticket(self.wh1, "T-DONE", 1, 10.0)
        self._ticket(self.wh1, "T-PICKUP", 1, 10.0, open_picking=True)
        self._ticket(self.wh1, "T-DRAFT", 1, 10.0, state="draft")
        numbers = {r["number"] for r in self._rows()}
        self.assertEqual(numbers, {"T-DONE"})

    def test_invoices_of_tickets_and_orders_are_not_counted_twice(self):
        order = self._sale(self.wh1, 2, 10.0, invoice=True)
        ticket = self._ticket(self.wh1, "T-FACT", 1, 10.0)
        invoice = self._invoice(1, 10.0)
        ticket.account_move = invoice
        numbers = [r["number"] for r in self._rows(warehouse_ids=[Command.clear()])]
        self.assertEqual(sorted(numbers), sorted([order.name, "T-FACT"]))

    # ---- filtros ---------------------------------------------------------------------------------
    def test_date_range(self):
        self._ticket(self.wh1, "T-0001", 1, 10.0)
        self.assertEqual(len(self._rows(date_from="2031-03-12", date_to="2031-03-12")), 1)
        self.assertEqual(self._rows(date_from="2031-03-13", date_to="2031-03-20"), [])
        self.assertEqual(len(self._rows(date_from="2031-03-01", date_to="2031-03-31")), 1)

    def test_dates_are_validated(self):
        with self.assertRaises(ValidationError):
            self._report(date_from="2031-04-01", date_to="2031-03-01")

    def test_one_several_or_all_warehouses(self):
        self._ticket(self.wh1, "T-1", 1, 10.0)
        self._ticket(self.wh2, "T-2", 1, 10.0)
        self.assertEqual({r["number"] for r in self._rows(warehouse_ids=[Command.set(self.wh2.ids)])}, {"T-2"})
        self.assertEqual(
            {r["number"] for r in self._rows(warehouse_ids=[Command.set((self.wh1 | self.wh2).ids)])},
            {"T-1", "T-2"},
        )
        # Sin elegir almacén salen todos (incluida la factura suelta, que no tiene almacén)
        self._invoice(1, 10.0)
        self.assertEqual(len(self._rows(warehouse_ids=[Command.clear()])), 3)
        # Elegir un almacén deja fuera lo que no tiene almacén
        self.assertEqual(len(self._rows(warehouse_ids=[Command.set(self.wh1.ids)])), 1)

    def test_users_with_assigned_warehouses_only_see_their_own(self):
        self._ticket(self.wh1, "T-1", 1, 10.0)
        self._ticket(self.wh2, "T-2", 1, 10.0)
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Tienda RENT",
                    "login": "tienda_rent",
                    "tz": "Europe/Madrid",
                    "group_ids": [Command.set(self.env.ref(f"{MODULE}.perm_va14_profit").ids)],
                    "allowed_warehouse_ids": [Command.set(self.wh2.ids)],
                }
            )
        )
        rows = self._report(warehouse_ids=[Command.clear()]).with_user(user)._get_rows()
        self.assertEqual([r["number"] for r in rows], ["T-2"])

    # ---- listado y Excel -----------------------------------------------------------------------------
    def test_show_creates_the_list(self):
        self._ticket(self.wh1, "T-1", 1, 7.0)
        report = self._report()
        action = report.action_show()
        self.assertEqual(action["res_model"], "todopintura.profitability.report.line")
        self.assertEqual(action["domain"], [("report_id", "=", report.id)])
        lines = self.env["todopintura.profitability.report.line"].search(action["domain"])
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.flag, "**")
        report.action_show()  # recalcula sin duplicar
        self.assertEqual(self.env["todopintura.profitability.report.line"].search_count(action["domain"]), 1)

    def _xlsx(self, report):
        action = report.action_export_xlsx()
        attachment = self.env["ir.attachment"].browse(
            int(action["url"].split("/web/content/")[1].split("?")[0])
        )
        with zipfile.ZipFile(io.BytesIO(attachment.raw)) as book:
            return book.read("xl/sharedStrings.xml").decode(), book.read("xl/worksheets/sheet1.xml").decode()

    def test_excel_has_the_columns_of_the_example_without_the_last_one(self):
        self._ticket(self.wh1, "T-0001", 1, 7.0)
        self._sale(self.wh1, 1, 10.0)
        strings, sheet = self._xlsx(self._report())
        for header in (
            "ALMACEN", "COMERCIAL", "ARTICULO", "DESCRIPCION", "NUMERO", "NOMBRE DE CLIENTE", "FECHA",
            "NUM.", "CANTIDAD", "P.COSTO", "P.V.P.", "BENEFIC.", "% Bº", "TIPO", "DOCUMENTO",
        ):
            self.assertIn(header, strings)
        self.assertIn("**", strings)
        self.assertIn("ALBARAN", strings)
        self.assertIn("Contado", strings)
        self.assertNotIn("TIKET", strings)
        # 15 columnas (A..O): sobra la P del Excel de ejemplo
        self.assertIn('ref="A1:O3"', sheet)

    # ---- menú ------------------------------------------------------------------------------------------
    def test_menu_and_permission_exist_and_only_direction_has_it(self):
        menu = self.env.ref(f"{MODULE}.menu_vt_profitability")
        self.assertEqual(menu.name, "Listado de rentabilidad")
        perm = self.env.ref(f"{MODULE}.perm_va14_profit")
        self.assertIn(self.env.ref(f"{MODULE}.group_cost_viewer"), perm.implied_ids)
        self.assertIn(perm, self.env.ref(f"{MODULE}.group_10_direccion").all_implied_ids)
        self.assertNotIn(perm, self.env.ref(f"{MODULE}.group_06_ventas_de_tiendas").all_implied_ids)
