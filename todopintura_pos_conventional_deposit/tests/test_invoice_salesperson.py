from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestInvoiceSalesperson(PosConventionalTestCommon):

    def _make_order(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        return order

    def test_invoice_uses_partner_salesperson(self):
        salesperson = self.env["res.users"].create({
            "name": "Comercial Test",
            "login": "comercial_test_invoice",
        })
        self.partner.commercial_partner_id.user_id = salesperson
        order = self._make_order()

        vals = order._prepare_invoice_vals()

        self.assertEqual(vals["invoice_user_id"], salesperson.id)

    def test_invoice_keeps_default_without_salesperson(self):
        self.partner.commercial_partner_id.user_id = False
        self.partner.user_id = False
        order = self._make_order()

        vals = order._prepare_invoice_vals()

        self.assertEqual(vals["invoice_user_id"], order.user_id.id)
