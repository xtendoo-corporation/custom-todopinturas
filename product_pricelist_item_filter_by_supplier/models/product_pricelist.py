from odoo import fields, models

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    # def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
    #     self.ensure_one()
    #     date = date or fields.Date.today()
    #     items = self.env['product.pricelist.item'].search([
    #         ('pricelist_id', '=', self.id),
    #         ('date_start', '<=', date),
    #         ('date_end', '>=', date),
    #     ])
    #
    #     results = {}
    #     for product, qty, partner in products_qty_partner:
    #         price = 0.0
    #         applicable_items = items.filtered(lambda item: item._is_applicable_for(product, qty))
    #         for item in applicable_items:
    #             price += item._compute_price(product, qty, uom_id, date, self.currency_id)
    #         results[product.id] = (price, False)
    #     return results
