from odoo import fields
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestTicketSimplificada(PosConventionalTestCommon):
    """Ticket de factura simplificada (80 mm): referencia + nombre en una línea, y debajo
    cantidad / precio / dto. / importe."""

    def _invoice(self, quantity=2.0, discount=55.0):
        product = self.env["product.product"].create(
            {
                "name": "KR.PALETINA TRIPLE DECORA Nº24 CON UN NOMBRE MUY LARGO PARA EL TICKET",
                "default_code": "23181677",
                "list_price": 10.0,
            }
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.invoice_journal.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": product.display_name,
                            "quantity": quantity,
                            "price_unit": 5.98,
                            "discount": discount,
                        },
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _html(self, move):
        report = self.env.ref("pos_conventional_receipt_custom.action_factura_simplificada_80mm")
        return report._render_qweb_html(report.report_name, move.ids)[0].decode()

    def test_ticket_layout(self):
        move = self._invoice()
        html = self._html(move)

        # Referencia y nombre completos en una sola línea, sin corchetes
        self.assertIn("23181677 KR.PALETINA TRIPLE DECORA Nº24 CON UN NOMBRE MUY LARGO PARA EL TICKET", html)
        self.assertNotIn("[23181677]", html)
        # Debajo: cantidad, precio con IVA antes del dto., descuento e importe (formato español)
        self.assertIn(">2<", html)
        self.assertIn("55 %", html)
        total = f"{move.invoice_line_ids.price_total:.2f}".replace(".", ",")
        self.assertIn(total, html)
        unit_incl = f"{move.invoice_line_ids.price_total / (2 * 0.45):.2f}".replace(".", ",")
        self.assertIn(unit_incl, html)
        # Totales y textos fijos
        self.assertIn("IMPORTE TOTAL", html)
        self.assertIn("IVA INCLUIDO", html)
        self.assertIn("GRACIAS POR SU VISITA", html)
        self.assertIn(move.name, html)

    def test_ticket_without_discount_has_no_percentage(self):
        html = self._html(self._invoice(quantity=1.0, discount=0.0))
        self.assertNotIn(" %</td>", html)
        self.assertIn("IMPORTE TOTAL", html)
