from unittest.mock import patch

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

    def _form_arch(self, model):
        if model == "sale.order":
            # The sale order notice view is shipped inactive: read its source.
            view = self.env.ref(
                "todopintura_extend_pos_conventional."
                "view_sale_order_form_inherit_pos_observations"
            )
            return f"<form>{view.arch}</form>"
        return self.env[model].get_view(view_type="form")["arch"]

    def test_labels_use_title_case_and_bold(self):
        for model in ("pos.order", "sale.order"):
            arch = self._form_arch(model)
            root = etree.fromstring(arch)
            for label in ("Vale Requerido:", "Autorizados:"):
                spans = [
                    span
                    for span in root.iter("span")
                    if (span.xpath("string()") or "").strip() == label
                ]
                self.assertTrue(spans, f"{model}: falta {label}")
                for span in spans:
                    classes = span.get("class", "").split()
                    self.assertIn("fw-bold", classes, f"{model}: {label}")
                    self.assertNotIn("text-uppercase", classes, f"{model}: {label}")
            self.assertNotIn("VALE REQUERIDO", arch)
            self.assertNotIn("AUTORIZADOS", arch)
            self.assertNotIn("REVISAR CRÉDITO", arch)
            self.assertIn("Revisar Crédito del Cliente", arch)
            for old in ("Estado de Crédito", "Proyectada"):
                self.assertNotIn(old, self._form_arch("pos.order"))

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


@tagged("post_install", "-at_install")
class TestCreditSummary(TransactionCase):
    """Natural-language credit summary of the POS order notice."""

    POLICY = {
        "current_location_name": False,
        "allowed_location_names": False,
        "pickup_people": False,
        "requires_voucher": False,
        "voucher_reference": False,
        "current_due": 0.0,
        "credit_limit": 0.0,
        "total_after": 0.0,
        "warning_message": False,
        "credit_sale_allowed": True,
        "location_allowed": True,
    }

    def _order(self, **policy):
        partner = self.env["res.partner"].create({"name": "Cliente resumen"})
        order = self.env["pos.order"].new({"partner_id": partner.id})
        data = dict(self.POLICY, **policy)
        with patch.object(
            type(order), "_get_conventional_credit_policy_data", return_value=data
        ):
            order._compute_partner_credit_policy()
        return order

    def test_available_credit_without_debt(self):
        order = self._order(credit_limit=500.0, total_after=0.0)
        self.assertEqual(order.partner_credit_remaining_amount, 500.0)
        self.assertEqual(order.partner_credit_excess_amount, 0.0)

    def test_available_credit_counts_the_current_order(self):
        order = self._order(credit_limit=500.0, current_due=80.0, total_after=200.0)
        self.assertEqual(order.partner_credit_remaining_amount, 300.0)

    def test_exceeding_the_limit_shows_the_excess(self):
        order = self._order(credit_limit=500.0, total_after=540.0)
        self.assertEqual(order.partner_credit_remaining_amount, 0.0)
        self.assertEqual(order.partner_credit_excess_amount, 40.0)

    def test_exactly_at_the_limit_is_not_an_excess(self):
        order = self._order(credit_limit=500.0, total_after=500.0)
        self.assertEqual(order.partner_credit_remaining_amount, 0.0)
        self.assertEqual(order.partner_credit_excess_amount, 0.0)

    def test_without_limit_there_is_no_available_amount(self):
        order = self._order(credit_limit=0.0, current_due=70.0, total_after=70.0)
        self.assertEqual(order.partner_credit_remaining_amount, 0.0)
        self.assertEqual(order.partner_credit_excess_amount, 0.0)

    def test_without_customer_everything_is_zero(self):
        order = self.env["pos.order"].new({})
        order._compute_partner_credit_policy()
        self.assertEqual(order.partner_credit_remaining_amount, 0.0)

    def test_view_uses_the_new_wording(self):
        arch = self.env["pos.order"].get_view(view_type="form")["arch"]
        for text in ("Crédito disponible:", "Supera el límite en", "Deuda pendiente:"):
            self.assertIn(text, arch)
        self.assertIn("partner_credit_remaining_amount", arch)
