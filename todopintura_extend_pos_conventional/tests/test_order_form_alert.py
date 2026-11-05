from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOrderFormAlertBanner(TransactionCase):
    """The yellow notice of the POS order form only shows when it has content."""

    NO_INFO = {
        "partner_id": True,
        "partner_requires_voucher": False,
        "partner_pickup_persons_display": False,
        "partner_credit_warning_message": False,
        "partner_current_total_due": 0.0,
        "partner_credit_limit_amount": 0.0,
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        arch = cls.env["pos.order"].get_view(view_type="form")["arch"]
        node = etree.fromstring(arch).xpath("//div[@name='credit_alert_container']")
        cls.expression = node[0].get("invisible")

    def _hidden(self, **values):
        context = dict(self.NO_INFO, **values)
        return bool(eval(self.expression, {}, context))  # noqa: S307

    def test_banner_exists_in_the_form(self):
        self.assertTrue(self.expression)

    def test_hidden_without_customer(self):
        self.assertTrue(self._hidden(partner_id=False))

    def test_hidden_when_the_customer_has_no_information(self):
        self.assertTrue(self._hidden())

    def test_visible_for_a_required_voucher(self):
        self.assertFalse(self._hidden(partner_requires_voucher=True))

    def test_visible_for_authorized_pickup_people(self):
        self.assertFalse(self._hidden(partner_pickup_persons_display="Juan"))

    def test_visible_for_a_credit_warning(self):
        self.assertFalse(self._hidden(partner_credit_warning_message="Revisar"))

    def test_visible_when_the_customer_has_debt(self):
        self.assertFalse(self._hidden(partner_current_total_due=10.0))

    def test_visible_when_the_customer_has_a_credit_limit(self):
        self.assertFalse(self._hidden(partner_credit_limit_amount=500.0))
