# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestXtdEffectsCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.env.user.company_id = cls.company.id
        cls.env.user.group_ids |= cls.env.ref(
            "account_payment_order.group_account_payment"
        )
        cls.journal = cls.company_data["default_journal_bank"]
        cls.invoice_line_account = cls.company_data["default_account_revenue"]

        cls.general_account = cls.env["account.account"].create(
            {
                "name": "Efectos comerciales en cartera",
                "code": "411000",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.pending_account = cls.env["account.account"].create(
            {
                "name": "Efectos comerciales pendientes de vencer",
                "code": "411001",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.discounted_account = cls.env["account.account"].create(
            {
                "name": "Deudas por efectos descontados Banco Santander",
                "code": "520001",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )

        cls.payment_method = cls.env.ref("account.account_payment_method_manual_in")
        cls.giro_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Giro",
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.journal.id,
                "payment_method_id": cls.payment_method.id,
                "company_id": cls.company.id,
                "xtd_manage_effects_discount": True,
                "xtd_pending_effects_account_id": cls.pending_account.id,
                "xtd_discounted_effects_account_id": cls.discounted_account.id,
            }
        )
        # Point the outstanding/bridge account of the auto-created payment
        # method line to the GENERAL effects account (411000): this is what
        # every payment hits natively at post time, discounted or not.
        cls.method_line = cls.env["account.payment.method.line"].search(
            [
                ("payment_method_id", "=", cls.payment_method.id),
                ("journal_id", "=", cls.journal.id),
            ],
            limit=1,
        )
        cls.method_line.payment_account_id = cls.general_account.id

        cls.partner = cls.env["res.partner"].create({"name": "Test Partner Giro"})

        # A second, unrelated payment mode with NO xtd flags at all, whose
        # bridge account is only ever reached by a plain manual "Registrar
        # pago" -- mirrors Pagaré in todopintura (several method lines/
        # journals for the same payment_method_id, no fixed one).
        cls.manual_bridge_account = cls.env["account.account"].create(
            {
                "name": "Pagos pendientes",
                "code": "572999",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.pagare_journal = cls.env["account.journal"].create(
            {
                "name": "Efectos a cobrar",
                "code": "EFCT",
                "type": "bank",
                "company_id": cls.company.id,
            }
        )
        cls.pagare_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Pagaré",
                "bank_account_link": "variable",
                "variable_journal_ids": [(6, 0, [cls.pagare_journal.id])],
                "payment_method_id": cls.payment_method.id,
                "company_id": cls.company.id,
            }
        )
        cls.pagare_method_line = cls.env["account.payment.method.line"].search(
            [
                ("payment_method_id", "=", cls.payment_method.id),
                ("journal_id", "=", cls.pagare_journal.id),
            ],
            limit=1,
        )
        cls.pagare_method_line.payment_account_id = cls.manual_bridge_account.id

        # Third mode: the "cadena de efectos" flow (confirmar -> generar ->
        # subir, no due-date branching) -- e.g. Pagaré with immediate
        # posting at order confirmation instead of at upload.
        cls.chain_bridge_account = cls.env["account.account"].create(
            {
                "name": "Deudores, efectos comerciales a cobrar (test)",
                "code": "441990",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.chain_remesado_account = cls.env["account.account"].create(
            {
                "name": "Efectos remesados al descuento (test)",
                "code": "441991",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.chain_bank_debt_account = cls.env["account.account"].create(
            {
                "name": "Deudas por efectos descontados (cadena, test)",
                "code": "520899",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        cls.chain_journal = cls.env["account.journal"].create(
            {
                "name": "Banco cadena efectos",
                "code": "CHJR",
                "type": "bank",
                "company_id": cls.company.id,
            }
        )
        cls.chain_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Pagaré cadena",
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.chain_journal.id,
                "payment_method_id": cls.payment_method.id,
                "company_id": cls.company.id,
                "xtd_effect_on_validate": True,
                "xtd_effect_chain_enabled": True,
                "xtd_chain_receivable_account_id": cls.chain_bridge_account.id,
                "xtd_chain_remesado_account_id": cls.chain_remesado_account.id,
                "xtd_chain_bank_debt_account_id": cls.chain_bank_debt_account.id,
            }
        )
        # Deliberately NOT setting payment_account_id on the method line here
        # -- that's the point of xtd_chain_receivable_account_id: create()
        # above must have synced it there automatically already.
        cls.chain_method_line = cls.env["account.payment.method.line"].search(
            [
                ("payment_method_id", "=", cls.payment_method.id),
                ("journal_id", "=", cls.chain_journal.id),
            ],
            limit=1,
        )

    def _create_customer_invoice(
        self, amount=100.0, invoice_date_due=None, mode=None
    ):
        with Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        ) as invoice_form:
            invoice_form.partner_id = self.partner
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.name = "Test product"
                invoice_line_form.quantity = 1
                invoice_line_form.price_unit = amount
                invoice_line_form.account_id = self.invoice_line_account
                invoice_line_form.tax_ids.clear()
        invoice_form.reference_type = "structured"
        invoice = invoice_form.save()
        invoice_form = Form(invoice)
        invoice_form.payment_mode_id = mode or self.giro_mode
        invoice = invoice_form.save()
        if invoice_date_due:
            invoice.invoice_date_due = invoice_date_due
        return invoice

    def _register_manual_payment(self, invoice, method_line):
        """Simulate a plain "Registrar pago" against `invoice`, using
        `method_line`'s own bridge account as outstanding -- no xtd
        machinery involved, exactly like a manually booked Pagaré payment."""
        receivable_line = invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and not line.reconciled
        )
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": invoice.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "journal_id": method_line.journal_id.id,
                "payment_method_line_id": method_line.id,
                "destination_account_id": receivable_line.account_id.id,
            }
        )
        payment.action_post()
        counterpart_line = payment._seek_for_lines()[1]
        (receivable_line + counterpart_line).reconcile()
        return payment

    def _create_and_upload_order(self, invoices, mode=None, journal=None):
        mode = mode or self.giro_mode
        journal = journal or self.journal
        invoices.action_post()
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "inbound",
                "payment_mode_id": mode.id,
                "journal_id": journal.id,
            }
        )
        self.env["account.invoice.payment.line.multi"].with_context(
            active_model="account.move", active_ids=invoices.ids
        ).create({}).run()
        order.draft2open()
        order.open2generated()
        order.generated2uploaded()
        return order
