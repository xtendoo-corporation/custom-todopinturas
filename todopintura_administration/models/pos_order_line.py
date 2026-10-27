from odoo import api, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    def _tp_get_price_and_discount(self):
        """Devuelve (PVP, % descuento) si la tarifa rebaja el PVP, o None."""
        self.ensure_one()
        order = self.order_id
        pricelist = order.pricelist_id or order.session_id.config_id.pricelist_id
        if not pricelist:
            return None
        product = self.product_id
        pricelist_price = pricelist._get_product_price(
            product, self.qty or 1.0, partner=order.partner_id, uom=product.uom_id
        )
        public_price = product.lst_price
        if public_price > 0 and public_price > pricelist_price:
            return public_price, (public_price - pricelist_price) / public_price * 100
        return None

    @api.onchange("product_id", "qty")
    def _onchange_product_id(self):
        """Muestra PVP + descuento de tarifa y recalcula los subtotales.

        El onchange nativo fija el precio de tarifa y calcula los subtotales
        con el descuento que tuviera la línea. Tras cambiar precio y descuento
        hay que recalcular los subtotales: si los valores finales coinciden con
        los iniciales, Odoo no vuelve a lanzar ``_onchange_qty`` y el subtotal
        quedaría con el descuento aplicado dos veces.
        """
        res = super()._onchange_product_id()
        for line in self.filtered("product_id"):
            price_and_discount = line._tp_get_price_and_discount()
            if price_and_discount:
                line.price_unit, line.discount = price_and_discount
            else:
                line.discount = 0.0
            line._onchange_qty()
        return res
