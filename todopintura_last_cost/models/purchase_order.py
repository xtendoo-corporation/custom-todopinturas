from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_approve(self, force=False):
        orders_to_update = self.filtered(lambda order: order.state != "purchase")
        res = super().button_approve(force=force)
        orders_to_update.filtered(
            lambda order: order.state == "purchase"
        )._update_last_purchase_cost()
        return res

    def _update_last_purchase_cost(self):
        """Escribe como coste del producto el precio del pedido recién confirmado.

        Solo afecta a productos cuya categoría usa el método «Último coste de
        compra». El precio es neto de descuentos, en la moneda de la empresa y
        en la unidad de medida del producto. Si el producto aparece en varias
        líneas del pedido prevalece la última.
        """
        for order in self:
            company = order.company_id
            price_by_product = {}
            lines = order.order_line.filtered(
                lambda line: not line.display_type
                and line.product_id
                and line.product_qty > 0
            ).sorted(lambda line: (line.sequence, line.id))
            for line in lines:
                product = line.product_id
                if product.categ_id.with_company(company).property_cost_method != "last":
                    continue
                price = line.with_company(company)._get_stock_move_price_unit()
                if price > 0:
                    price_by_product[product] = price
            for product, price in price_by_product.items():
                product.sudo().with_company(company).standard_price = price
