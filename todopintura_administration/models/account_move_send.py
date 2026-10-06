from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_pdf_report_id(self, move):
        """Si ni el cliente ni el diario fijan una plantilla, usar la factura
        Todo Pintura en lugar de la estándar de Odoo."""
        partner = move.commercial_partner_id.with_company(move.company_id)
        journal = move.journal_id.with_company(move.company_id)
        if not partner.invoice_template_pdf_report_id and not journal.invoice_template_pdf_report_id:
            report = self.env.ref(
                'todopintura_administration.action_report_factura_todopintura',
                raise_if_not_found=False,
            )
            if report and move._is_action_report_available(report):
                return report
        return super()._get_default_pdf_report_id(move)
