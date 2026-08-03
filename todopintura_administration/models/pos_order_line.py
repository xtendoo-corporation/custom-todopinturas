from odoo import models, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.onchange('product_id', 'qty')
    def _onchange_product_id(self):
        # Mantener lógica nativa y luego forzar visualización precio de lista + descuento
        res = super()._onchange_product_id()
        for line in self:
            try:
                order = line.order_id
                if not line.product_id or not order:
                    continue
                pricelist = order.pricelist_id or (order.session_id and order.session_id.config_id and order.session_id.config_id.pricelist_id)
                public_price = float(line.product_id.lst_price or 0.0)
                if pricelist:
                    price_unit = pricelist._get_product_price(line.product_id, line.qty or 1.0, partner=order.partner_id, uom=line.product_id.uom_id)
                    if public_price > price_unit and public_price > 0:
                        line.discount = (public_price - price_unit) / public_price * 100
                        line.price_unit = public_price
            except Exception:
                # No romper el onchange
                continue
        return res

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            v = dict(vals)
            try:
                if v.get('product_id') and v.get('order_id'):
                    order = self.env['pos.order'].browse(v.get('order_id'))
                    if order.exists():
                        product = self.env['product.product'].browse(v.get('product_id'))
                        qty = v.get('qty') or v.get('product_uom_qty') or 1.0
                        pricelist = order.pricelist_id or (order.session_id and order.session_id.config_id and order.session_id.config_id.pricelist_id)
                        if pricelist and product.exists():
                            pricelist_price = pricelist._get_product_price(product, qty, partner=order.partner_id, uom=product.uom_id)
                            public_price = float(product.lst_price or 0.0)
                            if public_price > pricelist_price and public_price > 0:
                                v['discount'] = (public_price - pricelist_price) / public_price * 100
                                v['price_unit'] = public_price
            except Exception:
                pass
            normalized.append(v)
        return super().create(normalized)

