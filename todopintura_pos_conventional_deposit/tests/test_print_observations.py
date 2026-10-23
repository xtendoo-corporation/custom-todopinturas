from odoo import fields
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import tagged

OBSERVATION = "Entregar por la puerta trasera\nLlamar antes de ir"


@tagged("post_install", "-at_install")
class TestPrintObservations(PosConventionalTestCommon):
    """Las observaciones del pedido de TPV salen bajo el número de factura/albarán."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "pos_can_edit_price" in cls.env.user._fields:
            cls.env.user.pos_can_edit_price = True

    def _order(self, observations=OBSERVATION, session=None):
        session = session or self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order, self.product)
        order.write({"pos_observations": observations})
        return order

    def _html(self, xmlid, record):
        report = self.env.ref(xmlid)
        return report._render_qweb_html(report.report_name, record.ids)[0].decode()

    def test_picking_observations_and_print_below_number(self):
        order = self._order()
        location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_deposit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, location.ids)],
            }
        )
        order.action_pay_deposit()
        picking = order.picking_ids
        self.assertTrue(picking)
        self.assertEqual(picking._tp_report_observations(), OBSERVATION)

        html = self._html(
            "todopintura_administration.action_report_albaran_todopintura", picking
        )
        number_pos = html.index(picking.name.split("/")[-1])
        obs_pos = html.index("Entregar por la puerta trasera")
        self.assertGreater(obs_pos, number_pos)
        self.assertIn("Llamar antes de ir", html)

    def test_picking_without_observations_prints_nothing_extra(self):
        order = self._order(observations=False)
        location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_deposit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, location.ids)],
            }
        )
        order.action_pay_deposit()
        self.assertFalse(order.picking_ids._tp_report_observations())

    def test_invoice_observations_and_print_below_number(self):
        order = self._order()
        other = self._order("Segunda observación", session=order.session_id)
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
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "quantity": 1.0,
                            "price_unit": 10.0,
                        },
                    )
                ],
            }
        )
        (order | other).with_context(skip_completeness_check=True).write(
            {"account_move": move.id}
        )
        self.assertEqual(
            move._tp_report_observations(), OBSERVATION + "\n\nSegunda observación"
        )

        html = self._html(
            "todopintura_administration.action_report_factura_todopintura", move
        )
        title_pos = html.index("FACTURA")
        obs_pos = html.index("Entregar por la puerta trasera")
        payment_pos = html.index("Forma de pago")  # las observaciones van tras el bloque número/forma de pago
        self.assertTrue(title_pos < payment_pos < obs_pos)
        self.assertIn("Segunda observación", html)


@tagged("post_install", "-at_install")
class TestObservationsAlbaranThenInvoice(PosConventionalTestCommon):
    """Albarán primero, factura después: la observación debe llegar a la factura."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "pos_can_edit_price" in cls.env.user._fields:
            cls.env.user.pos_can_edit_price = True
        config_vals = {
            "journal_id": cls.invoice_journal.id,
            "invoice_journal_id": cls.invoice_journal.id,
        }
        if "l10n_es_simplified_invoice_journal_id" in cls.pos_config._fields:
            config_vals["l10n_es_simplified_invoice_journal_id"] = cls.invoice_journal.id
        cls.pos_config.write(config_vals)
        cls.pay_later_pm = cls.env["pos.payment.method"].create(
            {"name": "Cuenta cliente obs test", "journal_id": cls.invoice_journal.id}
        )
        cls.pos_config.write({"payment_method_ids": [(4, cls.pay_later_pm.id)]})

    def _order(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order, self.product)
        order.write({"pos_observations": OBSERVATION})
        return order

    def test_deposit_albaran_then_invoice_keeps_observations(self):
        order = self._order()
        location = order.config_id.picking_type_id.default_location_src_id
        self.partner.commercial_partner_id.write(
            {
                "pos_deposit_sale_enabled": True,
                "pos_credit_location_ids": [(6, 0, location.ids)],
            }
        )
        order.action_pay_deposit()
        self.assertEqual(order.picking_ids._tp_report_observations(), OBSERVATION)

        invoice = order._create_conventional_deposit_invoice()
        self.assertEqual(invoice._tp_report_observations(), OBSERVATION)

    def test_credit_sale_albaran_then_invoice_keeps_observations(self):
        order = self._order()
        self.partner.commercial_partner_id.write({"pos_credit_sale_enabled": True})
        order.action_pos_convention_pay_with_method(self.pay_later_pm.id)
        sale = order.linked_sale_order_id
        self.assertTrue(sale)
        self.assertEqual(sale.pos_observations, OBSERVATION)
        if sale.state in ("draft", "sent"):
            sale.action_confirm()
        for line in sale.order_line.filtered(lambda l: not l.display_type):
            line.qty_delivered = line.product_uom_qty
        for picking in sale.picking_ids:
            self.assertEqual(picking._tp_report_observations(), OBSERVATION)

        invoice = sale._create_invoices()
        self.assertTrue(invoice)
        self.assertEqual(invoice._tp_report_observations(), OBSERVATION)
