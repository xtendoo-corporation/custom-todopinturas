from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _tp_report_title(self):
        self.ensure_one()
        if self.move_type in ('out_refund', 'in_refund'):
            return 'FACTURA RECTIFICATIVA Nº'
        return 'FACTURA Nº'

    def _tp_report_tax_summary(self):
        """Base, IVA por tipo y recargo de equivalencia por tipo."""
        self.ensure_one()
        iva, recargo = {}, {}
        sign = -1 if self.move_type in ('out_invoice', 'in_refund') else 1
        for line in self.line_ids.filtered('tax_line_id'):
            tax = line.tax_line_id
            is_re = 'recargo' in (tax.tax_group_id.name or '').lower()
            bucket = recargo if is_re else iva
            bucket[tax.amount] = bucket.get(tax.amount, 0.0) + sign * line.amount_currency
        return {
            'base': self.amount_untaxed,
            'iva': sorted(iva.items()),
            'recargo': sorted(recargo.items()),
            'total': self.amount_total,
        }
