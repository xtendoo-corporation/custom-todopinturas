from unittest.mock import patch

from odoo import fields
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import tagged

A4_REPORT = "todopintura_administration.report_factura_todopintura_document"
FAKE_PDF = b"%PDF-1.4 factura de prueba"


@tagged("post_install", "-at_install")
class TestInvoicePdfOnce(PosConventionalTestCommon):
    """El PDF de la factura se genera una sola vez: nunca dentro del cobro y,
    al imprimir el A4, se guarda como PDF oficial y se reutiliza."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "pos_can_edit_price" in cls.env.user._fields:
            cls.env.user.pos_can_edit_price = True

    def _invoiced_order(self, **ctx):
        order = self._make_draft_order(session=self._open_session(), partner=self.partner)
        self._add_line(order, product=self.product, qty=1.0)
        self._add_payment(order, payment_method=self.cash_pm)
        order.action_pos_order_paid()
        order.with_context(**ctx)._generate_pos_order_invoice()
        return order

    def _posted_invoice(self, partner=None):
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": (partner or self.partner).id,
            "journal_id": self.invoice_journal.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 10,
            })],
        })
        move.action_post()
        return move

    def _patch_render(self):
        return patch.object(
            type(self.env["ir.actions.report"]),
            "_render_qweb_pdf",
            autospec=True,
            return_value=(FAKE_PDF, "pdf"),
        )

    # ── Punto 1: el cobro no genera el PDF ──────────────────────────────────
    def test_pos_invoice_does_not_generate_pdf(self):
        with patch.object(type(self.env["account.move"]), "_generate_and_send", autospec=True) as gen:
            order = self._invoiced_order()
        self.assertTrue(order.account_move)
        gen.assert_not_called()
        self.assertFalse(order.account_move.invoice_pdf_report_id)

    def test_explicit_generate_pdf_context_is_respected(self):
        with patch.object(type(self.env["account.move"]), "_generate_and_send", autospec=True) as gen:
            self._invoiced_order(generate_pdf=True)
        gen.assert_called_once()

    # ── Punto 2: el A4 se genera una vez y se reutiliza ─────────────────────
    def test_a4_pdf_rendered_once_and_stored_as_official(self):
        move = self._posted_invoice()
        self.assertTrue(move._tp_a4_is_default_pdf_template())
        with self._patch_render() as render:
            first = move._tp_get_a4_invoice_pdf()
            second = move._tp_get_a4_invoice_pdf()
        self.assertEqual(render.call_count, 1)
        self.assertEqual(render.call_args.args[1], A4_REPORT)
        self.assertEqual(first, FAKE_PDF)
        self.assertEqual(second, FAKE_PDF)
        self.assertEqual(move.invoice_pdf_report_id.raw, FAKE_PDF)
        self.assertEqual(move.invoice_pdf_report_id.res_field, "invoice_pdf_report_file")
        self.assertTrue(move.is_move_sent)

    def test_existing_official_pdf_is_reused(self):
        move = self._posted_invoice()
        self.env["account.move.send"]._link_invoice_documents({
            move: {"pdf_attachment_values": {
                "name": "previo.pdf",
                "raw": b"%PDF-1.4 previo",
                "mimetype": "application/pdf",
                "res_model": move._name,
                "res_id": move.id,
                "res_field": "invoice_pdf_report_file",
            }},
        })
        with self._patch_render() as render:
            pdf = move._tp_get_a4_invoice_pdf()
        render.assert_not_called()
        self.assertEqual(pdf, b"%PDF-1.4 previo")

    def test_other_default_template_is_neither_reused_nor_stored(self):
        partner = self.env["res.partner"].create({
            "name": "Cliente con plantilla estándar",
            "invoice_template_pdf_report_id": self.env.ref("account.account_invoices").id,
        })
        move = self._posted_invoice(partner=partner)
        self.assertFalse(move._tp_a4_is_default_pdf_template())
        with self._patch_render() as render:
            move._tp_get_a4_invoice_pdf()
            move._tp_get_a4_invoice_pdf()
        self.assertEqual(render.call_count, 2)
        self.assertFalse(move.invoice_pdf_report_id)

    def test_draft_invoice_is_not_stored(self):
        move = self._posted_invoice()
        move.button_draft()
        with self._patch_render() as render:
            move._tp_get_a4_invoice_pdf()
        render.assert_called_once()
        self.assertFalse(move.invoice_pdf_report_id)
