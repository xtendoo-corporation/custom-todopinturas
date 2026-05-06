from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase, tagged


@tagged("post_install", "-at_install")
class TestResPartnerVatConstraint(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Test Company B"})

    @classmethod
    def _create_partner(cls, name, vat, company):
        return cls.partner_model.create(
            {
                "name": name,
                "vat": vat,
                "company_id": company.id if company else False,
            }
        )

    def test_duplicate_vat_same_company_is_blocked(self):
        vat = "DNI-SAME-COMPANY"
        self._create_partner("Partner A1", vat, self.company_a)

        with self.assertRaises(ValidationError):
            self._create_partner("Partner A2", vat, self.company_a)

    def test_duplicate_vat_different_companies_is_allowed(self):
        vat = "DNI-DIFF-COMPANY"
        partner_a = self._create_partner("Partner A", vat, self.company_a)
        partner_b = self._create_partner("Partner B", vat, self.company_b)

        self.assertTrue(partner_a)
        self.assertTrue(partner_b)

    def test_global_partner_vat_blocks_any_other_scope(self):
        vat = "DNI-GLOBAL-BLOCK"
        self._create_partner("Partner Global", vat, False)

        with self.assertRaises(ValidationError):
            self._create_partner("Partner A", vat, self.company_a)

        with self.assertRaises(ValidationError):
            self._create_partner("Partner B", vat, self.company_b)

        with self.assertRaises(ValidationError):
            self._create_partner("Partner Global 2", vat, False)

    def test_write_detects_conflicts_on_company_or_vat_changes(self):
        vat = "DNI-WRITE-COMPANY"
        self._create_partner("Partner A", vat, self.company_a)
        partner_b = self._create_partner("Partner B", vat, self.company_b)

        with self.assertRaises(ValidationError):
            partner_b.write({"company_id": self.company_a.id})

        global_vat = "DNI-GLOBAL-WRITE"
        self._create_partner("Partner Global", global_vat, False)
        partner_c = self._create_partner("Partner C", "DNI-OTHER", self.company_b)

        with self.assertRaises(ValidationError):
            partner_c.write({"vat": global_vat})

    def test_write_same_values_on_self_does_not_fail(self):
        vat = "DNI-SELF-EDIT"
        partner = self._create_partner("Partner Self", vat, self.company_a)

        partner.write({"name": "Partner Self Updated"})
        partner.write({"vat": vat, "company_id": self.company_a.id})

        self.assertEqual(partner.vat, vat)
        self.assertEqual(partner.company_id, self.company_a)

