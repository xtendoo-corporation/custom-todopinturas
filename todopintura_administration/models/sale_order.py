from odoo import models, tools


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _tp_report_title(self):
        self.ensure_one()
        if self.state in ('draft', 'sent'):
            return 'PRESUPUESTO Nº'
        return 'PEDIDO Nº'

    def _tp_report_date_str(self):
        """Fecha extendida (6 DE OCTUBRE DE 2026), igual que en albarán y factura."""
        self.ensure_one()
        if not self.date_order:
            return ''
        return tools.format_date(
            self.env, self.date_order, lang_code=self.partner_id.lang or self.env.lang,
            date_format="d 'DE' MMMM 'DE' y",
        ).upper()

    def _tp_report_tax_summary(self):
        """Base, IVA por tipo y recargo de equivalencia por tipo."""
        self.ensure_one()
        iva, recargo = {}, {}
        for line in self.order_line.filtered(lambda l: not l.display_type):
            res = line.tax_ids.compute_all(
                line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                currency=self.currency_id,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=self.partner_shipping_id,
            )
            for tax_vals in res['taxes']:
                tax = self.env['account.tax'].browse(tax_vals['id'])
                is_re = 'recargo' in (tax.tax_group_id.name or '').lower()
                bucket = recargo if is_re else iva
                bucket[tax.amount] = bucket.get(tax.amount, 0.0) + tax_vals['amount']
        return {
            'base': self.amount_untaxed,
            'iva': sorted(iva.items()),
            'recargo': sorted(recargo.items()),
            'total': self.amount_total,
        }
