from odoo import api, fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    display_final_price = fields.Monetary(
        string="Precio final",
        currency_field="currency_id",
        compute="_compute_display_price_metrics",
        help="Precio unitario final que aplica la regla para la cantidad mínima o 1 unidad.",
    )
    display_total_price = fields.Monetary(
        string="Precio total",
        currency_field="currency_id",
        compute="_compute_display_price_metrics",
        help="Importe total calculado con la cantidad mínima de la regla o 1 unidad.",
    )
    display_cost_price = fields.Monetary(
        string="Coste",
        currency_field="currency_id",
        compute="_compute_display_price_metrics",
        help="Coste unitario del producto convertido a la moneda de la tarifa.",
        groups="base.group_user",
    )
    display_margin_amount = fields.Monetary(
        string="Margen",
        currency_field="currency_id",
        compute="_compute_display_price_metrics",
        help="Margen unitario: precio final menos coste.",
        groups="base.group_user",
    )
    display_margin_percent = fields.Float(
        string="Margen %",
        compute="_compute_display_price_metrics",
        digits=(16, 2),
        help="Porcentaje de margen sobre el precio final unitario.",
        groups="base.group_user",
    )

    @api.depends(
        "product_id",
        "product_id.standard_price",
        "product_id.cost_currency_id",
        "product_id.uom_id",
        "product_tmpl_id",
        "product_tmpl_id.standard_price",
        "product_tmpl_id.cost_currency_id",
        "product_tmpl_id.list_price",
        "product_tmpl_id.uom_id",
        "min_quantity",
        "compute_price",
        "fixed_price",
        "percent_price",
        "price_discount",
        "price_markup",
        "price_round",
        "price_surcharge",
        "price_min_margin",
        "price_max_margin",
        "base",
        "base_pricelist_id",
        "base_pricelist_id.currency_id",
        "pricelist_id",
        "pricelist_id.currency_id",
        "currency_id",
        "company_id",
    )
    def _compute_display_price_metrics(self):
        today = fields.Date.context_today(self)
        company = self.env.company
        for item in self:
            item.display_final_price = 0.0
            item.display_total_price = 0.0
            item.display_cost_price = 0.0
            item.display_margin_amount = 0.0
            item.display_margin_percent = 0.0

            product = item._get_display_metric_product()
            if not product or not item.currency_id or not product.uom_id:
                continue

            quantity = item.min_quantity if item.min_quantity > 0 else 1.0
            final_price = item._compute_price(
                product,
                quantity,
                product.uom_id,
                today,
                currency=item.currency_id,
            )
            cost_price = product.standard_price
            if product.cost_currency_id and product.cost_currency_id != item.currency_id:
                cost_price = product.cost_currency_id._convert(
                    cost_price,
                    item.currency_id,
                    item.company_id or company,
                    today,
                    round=False,
                )

            margin_amount = final_price - cost_price
            item.display_final_price = final_price
            item.display_total_price = final_price * quantity
            item.display_cost_price = cost_price
            item.display_margin_amount = margin_amount
            item.display_margin_percent = final_price and (margin_amount / final_price) * 100 or 0.0

    def _get_display_metric_product(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id
        if self.product_tmpl_id.product_variant_id:
            return self.product_tmpl_id.product_variant_id
        return self.product_tmpl_id.product_variant_ids[:1]

