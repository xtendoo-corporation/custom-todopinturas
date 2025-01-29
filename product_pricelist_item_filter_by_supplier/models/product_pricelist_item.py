from odoo import fields, models


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
