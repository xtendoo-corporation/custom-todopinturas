from odoo import api, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.depends_context("company")
    @api.depends("product_categ_id.property_cost_method")
    def _compute_cost_method(self):
        for quant in self:
            cost_method = (
                quant.product_categ_id.with_company(quant.company_id).property_cost_method
                or (quant.company_id or self.env.company).cost_method
            )
            quant.cost_method = "standard" if cost_method == "last" else cost_method
