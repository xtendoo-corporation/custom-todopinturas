# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command, fields
from odoo.tests import tagged

from .common import TodopinturaTestCase

MODULE = "todopintura_user_groups"
REPORT = f"{MODULE}.report_ticket_closing_document"
DAY = "2031-03-12"  # un día sin datos reales en la BD


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestTicketClosing(TodopinturaTestCase):
    """Listado cierre de tickets: tickets y facturas hechos en el día, por tienda."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env["stock.warehouse"]
        cls.ronda = Warehouse.create({"name": "Sucursal Ronda TC", "code": "RTC"})
        cls.lora = Warehouse.create({"name": "Sucursal Lora TC", "code": "LTC"})
        cls.configs = {}
        for warehouse in (cls.ronda, cls.lora):
            config = cls.env["pos.config"].create(
                {"name": f"TPV {warehouse.code}", "picking_type_id": warehouse.pos_type_id.id}
            )
            cls.configs[warehouse] = cls.env["pos.session"].create({"config_id": config.id})
        Partner = cls.env["res.partner"]
        cls.pintor = Partner.create({"name": "VENTAS CONTADO - PINTOR -", "ref": "1000777"})
        cls.jose = Partner.create({"name": "JOSE BASILIO HERNANDEZ VEGA", "ref": "16148"})
        cls.pricelist = cls.env["product.pricelist"].search(
            [("company_id", "in", [False, cls.env.company.id])], limit=1
        ) or cls.env["product.pricelist"].create({"name": "Tarifa TC"})
        cls.env.user.tz = "Europe/Madrid"

    @classmethod
    def _ticket(cls, warehouse, number, amount, partner=None, when=f"{DAY} 09:30:00", state="paid"):
        return cls.env["pos.order"].create(
            {
                "name": number,
                "pos_reference": number,
                "session_id": cls.configs[warehouse].id,
                "pricelist_id": cls.pricelist.id,
                "partner_id": partner.id if partner else False,
                "date_order": when,
                "state": state,
                "amount_tax": 0,
                "amount_total": amount,
                "amount_paid": amount,
                "amount_return": 0,
            }
        )

    @classmethod
    def _invoice(cls, partner, amount, move_type="out_invoice", date=DAY):
        move = cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": partner.id,
                "invoice_date": date,
                "invoice_line_ids": [
                    Command.create({"name": "Línea", "quantity": 1, "price_unit": amount, "tax_ids": [Command.clear()]})
                ],
            }
        )
        move.action_post()
        return move

    def _closing(self, **values):
        return self.env["todopintura.ticket.closing"].create({"date": DAY, **values})

    def _store(self, data, warehouse):
        return next(s for s in data["stores"] if s["name"] == warehouse.name.upper())

    # ---- datos -----------------------------------------------------------------------
    def test_tickets_are_listed_by_store_with_their_total(self):
        self._ticket(self.ronda, "T-0002", 95.36, self.pintor, f"{DAY} 10:00:00")
        self._ticket(self.ronda, "T-0001", 8.53, self.pintor, f"{DAY} 09:30:00")
        self._ticket(self.ronda, "T-0003", 6.59, self.jose, f"{DAY} 11:00:00")
        self._ticket(self.lora, "T-1001", 10.0, None, f"{DAY} 12:00:00")
        data = self._closing()._get_data()
        self.assertEqual([s["name"] for s in data["stores"]], ["SUCURSAL LORA TC", "SUCURSAL RONDA TC"])
        ronda = self._store(data, self.ronda)
        self.assertEqual([r["number"] for r in ronda["rows"]], ["T-0001", "T-0002", "T-0003"])  # por hora
        self.assertAlmostEqual(ronda["tickets_total"], 110.48)
        self.assertEqual(ronda["rows"][0]["customer_code"], "1000777")
        self.assertEqual(ronda["rows"][0]["customer_name"], "VENTAS CONTADO - PINTOR -")
        self.assertFalse(ronda["has_invoices"])
        self.assertAlmostEqual(data["tickets_total"], 120.48)
        self.assertEqual(data["count"], 4)

    def test_only_the_requested_day_counts_in_the_users_time_zone(self):
        # Madrid (UTC+1 en marzo): 22:30 UTC del 12 = 23:30 del 12; 23:30 UTC = 00:30 del 13
        self._ticket(self.ronda, "T-IN", 5.0, when=f"{DAY} 22:30:00")
        self._ticket(self.ronda, "T-OUT-LATE", 7.0, when=f"{DAY} 23:30:00")
        self._ticket(self.ronda, "T-OUT-EARLY", 9.0, when="2031-03-11 22:30:00")
        rows = self._closing()._get_data()["stores"][0]["rows"]
        self.assertEqual([r["number"] for r in rows], ["T-IN"])

    def test_ticket_number_is_the_short_reference_of_the_ticket(self):
        order = self._ticket(self.ronda, "TPV Tienda - 000123", 5.0)
        order.pos_reference = "260-2-000123"
        rows = self._closing()._get_data()["stores"][0]["rows"]
        self.assertEqual(rows[0]["number"], "260-2-000123")

    def test_draft_and_cancelled_orders_are_not_listed(self):
        self._ticket(self.ronda, "T-OK", 5.0)
        self._ticket(self.ronda, "T-DRAFT", 7.0, state="draft")
        self._ticket(self.ronda, "T-CANCEL", 9.0, state="cancel")
        rows = self._closing()._get_data()["stores"][0]["rows"]
        self.assertEqual([r["number"] for r in rows], ["T-OK"])

    def test_invoices_of_the_day_are_listed_apart_from_tickets(self):
        self._ticket(self.ronda, "T-0001", 20.0, self.pintor)
        invoice = self._invoice(self.jose, 100.0)
        refund = self._invoice(self.jose, 30.0, move_type="out_refund")
        data = self._closing()._get_data()
        self.assertTrue(data["has_invoices"])
        store = next(s for s in data["stores"] if s["has_invoices"])
        numbers = {r["number"]: r for r in store["rows"]}
        self.assertEqual(numbers[invoice.name]["kind"], "invoice")
        self.assertAlmostEqual(numbers[invoice.name]["amount"], 100.0)
        self.assertAlmostEqual(numbers[refund.name]["amount"], -30.0)
        self.assertAlmostEqual(store["invoices_total"], 70.0)
        self.assertEqual(data["tickets_total"], 20.0)
        self.assertAlmostEqual(data["total"], 90.0)

    def test_invoices_of_a_ticket_are_not_counted_twice(self):
        invoice = self._invoice(self.jose, 50.0)
        ticket = self._ticket(self.ronda, "T-FACT", 50.0, self.jose)
        ticket.account_move = invoice
        data = self._closing()._get_data()
        numbers = [r["number"] for s in data["stores"] for r in s["rows"]]
        self.assertEqual(numbers, ["T-FACT"])

    def test_invoices_of_other_days_are_not_listed(self):
        self._invoice(self.jose, 50.0, date="2031-03-11")
        self.assertEqual(self._closing()._get_data()["stores"], [])

    def test_warehouse_filter(self):
        self._ticket(self.ronda, "T-R", 5.0)
        self._ticket(self.lora, "T-L", 7.0)
        data = self._closing(warehouse_ids=[Command.set(self.lora.ids)])._get_data()
        self.assertEqual([s["name"] for s in data["stores"]], ["SUCURSAL LORA TC"])

    def test_users_with_assigned_warehouses_only_see_their_own(self):
        self._ticket(self.ronda, "T-R", 5.0)
        self._ticket(self.lora, "T-L", 7.0)
        store = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Tienda TC",
                    "login": "tienda_tc",
                    "tz": "Europe/Madrid",
                    "group_ids": [Command.set(self.env.ref(f"{MODULE}.perm_va14_tickets").ids)],
                    "allowed_warehouse_ids": [Command.set(self.ronda.ids)],
                }
            )
        )
        data = self._closing(warehouse_ids=[Command.set((self.ronda | self.lora).ids)]).with_user(store)._get_data()
        self.assertEqual([s["name"] for s in data["stores"]], ["SUCURSAL RONDA TC"])

    # ---- informe impreso ------------------------------------------------------------------
    def _html(self, closing):
        html = self.env["ir.actions.report"]._render_qweb_html(REPORT, closing.ids)[0]
        return html.decode() if isinstance(html, bytes) else html

    def test_report_prints_title_date_columns_tickets_and_total(self):
        self._ticket(self.ronda, "T-0001", 8.53, self.pintor)
        self._ticket(self.ronda, "T-0002", 95.36, self.jose)
        html = self._html(self._closing())
        for text in (
            "LISTADO CIERRE DE TICKETS", "Fecha.-", "12.03.31", "Pagina.-", "N°TICKET", "FECHA",
            "N°CLIENTE", "IMPORTE", "SUCURSAL RONDA TC", "T-0001", "12/03/31",
            "1000777", "VENTAS CONTADO - PINTOR -", "JOSE BASILIO HERNANDEZ VEGA", "TOTAL TICKETS",
        ):
            self.assertIn(text, html)
        self.assertTrue("103.89" in html or "103,89" in html)  # 8,53 + 95,36
        self.assertNotIn("TOTAL GENERAL", html)  # una sola tienda
        self.assertNotIn("TOTAL FACTURAS", html)

    def test_report_shows_invoices_and_the_general_total(self):
        self._ticket(self.ronda, "T-0001", 20.0, self.pintor)
        self._ticket(self.lora, "T-1001", 10.0, self.pintor)
        invoice = self._invoice(self.jose, 100.0)
        html = self._html(self._closing())
        self.assertIn("TOTAL GENERAL", html)
        self.assertIn("TOTAL FACTURAS", html)
        self.assertIn(f"FAC", html)
        self.assertIn(invoice.name, html)

    def test_report_without_documents_says_so(self):
        html = self._html(self._closing(date="2031-01-01"))
        self.assertIn("No hay tickets ni facturas en este día", html)

    def test_print_button_opens_the_report(self):
        action = self._closing().action_print()
        self.assertEqual(action["report_name"], REPORT)

    # ---- menú ------------------------------------------------------------------------------------
    def test_menu_and_permission_exist(self):
        menu = self.env.ref(f"{MODULE}.menu_vt_ticket_closing")
        self.assertEqual(menu.name, "Listado cierre de tickets")
        self.assertEqual(menu.parent_id, self.env.ref(f"{MODULE}.menu_vt_lists_group"))
        self.assertIn(
            self.env.ref(f"{MODULE}.perm_va14_tickets"),
            self.env.ref(f"{MODULE}.group_06_ventas_de_tiendas").implied_ids,
        )
