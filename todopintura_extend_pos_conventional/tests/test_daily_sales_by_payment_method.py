# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestDailySalesByPaymentMethod(PosConventionalTestCommon):
    """Venta diaria: las ventas de cada método de pago, con su total, una tras otra."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "pos_can_edit_price" in cls.env.user._fields:
            cls.env.user.pos_can_edit_price = True

    def _paid_order(self, session, method, amount):
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        order.write({"amount_total": amount, "amount_paid": amount})
        self._add_payment(order, method, amount)
        order.action_pos_order_paid()
        return order

    def _details(self, session):
        return self.env["report.point_of_sale.report_saledetails"].get_sale_details(
            session_ids=session.ids
        )

    def test_sales_are_grouped_by_payment_method_with_their_totals(self):
        session = self._open_session()
        cash_1 = self._paid_order(session, self.cash_pm, 10.0)
        card = self._paid_order(session, self.card_pm, 25.5)
        cash_2 = self._paid_order(session, self.cash_pm, 4.0)
        details = self._details(session)
        groups = {g["name"]: g for g in details["payments_detail"]}
        self.assertEqual(set(groups), {self.cash_pm.name, self.card_pm.name})
        cash = groups[self.cash_pm.name]
        self.assertEqual(cash["count"], 2)
        self.assertAlmostEqual(cash["total"], 14.0)
        self.assertEqual(
            [l["amount"] for l in cash["lines"]], [10.0, 4.0]
        )
        self.assertEqual(
            {l["order"] for l in cash["lines"]},
            {cash_1.pos_reference or cash_1.name, cash_2.pos_reference or cash_2.name},
        )
        self.assertEqual(groups[self.card_pm.name]["count"], 1)
        self.assertAlmostEqual(groups[self.card_pm.name]["total"], 25.5)
        self.assertAlmostEqual(details["payments_detail_total"], 39.5)
        self.assertEqual(details["payments_detail_count"], 3)
        self.assertEqual(card.amount_paid, 25.5)

    def test_methods_are_listed_one_after_another(self):
        session = self._open_session()
        self._paid_order(session, self.card_pm, 5.0)
        self._paid_order(session, self.cash_pm, 7.0)
        self._paid_order(session, self.card_pm, 3.0)
        names = [g["name"] for g in self._details(session)["payments_detail"]]
        self.assertEqual(len(names), len(set(names)))  # cada método una sola vez
        self.assertEqual(len(names), 2)

    def test_refunds_subtract_from_their_method(self):
        session = self._open_session()
        self._paid_order(session, self.cash_pm, 10.0)
        self._paid_order(session, self.cash_pm, -3.0)
        group = self._details(session)["payments_detail"][0]
        self.assertAlmostEqual(group["total"], 7.0)

    def test_draft_orders_are_not_reported(self):
        session = self._open_session()
        self._paid_order(session, self.cash_pm, 10.0)
        draft = self._make_draft_order(session, partner=self.partner)
        self._add_line(draft)
        details = self._details(session)
        self.assertEqual(details["payments_detail_count"], 1)

    def test_report_prints_each_method_with_its_total(self):
        session = self._open_session()
        self._paid_order(session, self.cash_pm, 10.0)
        self._paid_order(session, self.card_pm, 25.5)
        html = self.env["ir.actions.report"]._render_qweb_html(
            "point_of_sale.report_saledetails", session.ids
        )[0]
        html = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Ventas por método de pago", html)
        self.assertIn(f"Total {self.cash_pm.name}", html)
        self.assertIn(f"Total {self.card_pm.name}", html)
        # Orden: cada método con su bloque y, debajo, las tablas de impuestos y pagos
        # (con el total) como cierre del informe.
        payments_at = html.index('id="payments"')
        self.assertLess(html.index(f"Total {self.cash_pm.name}"), html.index('id="taxe_sales"'))
        self.assertLess(html.index(f"Total {self.card_pm.name}"), html.index('id="taxe_sales"'))
        self.assertLess(html.index('id="taxe_sales"'), payments_at)
        # El total es el de la tabla de pagos del informe estándar
        total_paid = self.env["report.point_of_sale.report_saledetails"].get_sale_details(
            session_ids=session.ids
        )["currency"]["total_paid"]
        self.assertAlmostEqual(total_paid, 35.5)
        self.assertTrue("35.50" in html or "35,50" in html[payments_at:])

    def test_initial_products_listing_is_removed_and_totals_close_the_report(self):
        """Ya no se imprime el listado inicial de productos por familia («Ventas»); las
        tablas de impuestos y pagos (con el total) quedan debajo del desglose."""
        session = self._open_session()
        order = self._paid_order(session, self.cash_pm, 10.0)
        html = self.env["ir.actions.report"]._render_qweb_html(
            "point_of_sale.report_saledetails", session.ids
        )[0]
        html = html.decode() if isinstance(html, bytes) else html
        self.assertNotIn('id="sales"', html)
        self.assertNotIn(order.lines.product_id.display_name, html)
        breakdown_at = html.index("Ventas por método de pago")
        self.assertLess(breakdown_at, html.index('id="taxe_sales"'))
        self.assertLess(html.index('id="taxe_sales"'), html.index('id="payments"'))
        self.assertNotIn("Total ventas", html)
        self.assertIn('id="discounts"', html)  # el resto del informe se mantiene

    def test_no_sales_no_section(self):
        session = self._open_session()
        html = self.env["ir.actions.report"]._render_qweb_html(
            "point_of_sale.report_saledetails", session.ids
        )[0]
        html = html.decode() if isinstance(html, bytes) else html
        self.assertNotIn("Ventas por método de pago", html)
