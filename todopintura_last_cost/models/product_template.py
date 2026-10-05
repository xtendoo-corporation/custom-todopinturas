from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends_context("company")
    @api.depends("categ_id.property_cost_method")
    def _compute_cost_method(self):
        """El «último coste de compra» se valora como precio estándar.

        Todo el código de valoración del núcleo distingue únicamente
        standard/fifo/average, así que el producto expone «standard» y el
        coste se actualiza al confirmar el pedido de compra.
        """
        for product_template in self:
            company = product_template.company_id
            if not company or self.env.company.filtered_domain([("id", "child_of", company.id)]):
                company = self.env.company
            cost_method = (
                product_template.categ_id.with_company(company).property_cost_method
                or company.cost_method
            )
            product_template.cost_method = "standard" if cost_method == "last" else cost_method
