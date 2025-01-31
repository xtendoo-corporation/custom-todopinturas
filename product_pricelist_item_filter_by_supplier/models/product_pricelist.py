from odoo import api, fields, models, _
from odoo.exceptions import UserError

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

    def _compute_price_rule(
            self, products, quantity, currency=None, uom=None, date=False, compute_price=True,
            **kwargs
    ):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

        Note: self and self.ensure_one()

        :param products: recordset of products (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param currency: record of currency (res.currency)
                         note: currency.ensure_one()
        :param uom: unit of measure (uom.uom record)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions
        :type date: date or datetime
        :param bool compute_price: whether the price should be computed (default: True)

        :returns: product_id: (price, pricelist_rule)
        :rtype: dict
        """
        self and self.ensure_one()  # self is at most one record

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        # Fetch all rules potentially matching specified products/templates/categories and date
        rules = self._get_applicable_rules(products, date, **kwargs)

        results = {}
        for product in products:
            suitable_rule = self.env['product.pricelist.item']
            product_uom = product.uom_id
            target_uom = uom or product_uom  # If no uom is specified, fall back on the product uom

            # Compute quantity in product uom because pricelist rules are specified
            # w.r.t product default UoM (min_quantity, price_surchage, ...)
            if target_uom != product_uom:
                qty_in_product_uom = target_uom._compute_quantity(
                    quantity, product_uom, raise_if_failure=False
                )
            else:
                qty_in_product_uom = quantity

            prioritized_rules = sorted(rules, key=lambda r: (
                r.product_id and r.product_id == product,
                r.categ_id and r.filter_supplier_id,
                not r.filter_supplier_id
            ), reverse=True)

            for rule in prioritized_rules:
                if rule._is_applicable_for(product, qty_in_product_uom):
                    if rule.filter_supplier_id and rule.filter_supplier_id.id not in product.seller_ids.partner_id.mapped(
                        'id'):
                        continue  # Skip this rule if supplier does not match
                    suitable_rule = rule
                    break

            if compute_price:
                price = suitable_rule._compute_price(
                    product, quantity, target_uom, date=date, currency=currency)
            else:
                # Skip price computation when only the rule is requested.
                price = 0.0
            results[product.id] = (price, suitable_rule.id)

        return results
