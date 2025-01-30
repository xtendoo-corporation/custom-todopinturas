from odoo import fields, models, api, _
from odoo.tools import format_datetime, formatLang

class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    filter_supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Filtro proveedor",
        help="Only match prices from the selected supplier",
    )

    def _compute_price(self, product, quantity, uom, date, currency=None):
        result = 0.0
        if not self.filter_supplier_id:
            result = super()._compute_price(product, quantity, uom, date, currency)

        if self.filter_supplier_id and self.filter_supplier_id.id in product.seller_ids.partner_id.mapped('id'):

            result = super()._compute_price(product, quantity, uom, date, currency)

        return result


    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
                 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge', 'filter_supplier_id')
    def _compute_name_and_price(self):
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = _("Category: %s", item.categ_id.display_name)
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = _("Product: %s", item.product_tmpl_id.display_name)
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = _("Variant: %s", item.product_id.display_name)
            elif item.applied_on == '3_global' and item.filter_supplier_id:
                item.name = _("All products with Supplier: %s", item.filter_supplier_id.display_name)
            else:
                item.name = _("All Products")

            if item.compute_price == 'fixed':
                item.price = formatLang(
                    item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
            elif item.compute_price == 'percentage':
                item.price = _("%s %% discount", item.percent_price)
            else:
                item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount,
                               price=item.price_surcharge)
