from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _onchange_product_id(self):
        # Mantener la lógica nativa y luego aplicar la visualización de precio/lista
        result = super()._onchange_product_id()

        if self.product_id and self.order_id and self.order_id.pricelist_id:
            pricelist = self.order_id.pricelist_id
            try:
                qty = self.product_uom_qty or 1.0
                pricelist_price = pricelist._get_product_price(
                    self.product_id, qty, partner=self.order_id.partner_id, uom=self.product_uom
                )
                public_price = float(self.product_id.lst_price or 0.0)
                if public_price > pricelist_price and public_price > 0:
                    self.discount = (public_price - pricelist_price) / public_price * 100
                    # Mostrar precio original (lista) y dejar el descuento como porcentaje
                    self.price_unit = public_price
                else:
                    # No hay descuento de tarifa sobre el precio de lista: dejar comportamiento por defecto
                    pass
            except Exception:
                # No interrumpir el onchange si ocurre un error de tipos o calculo
                pass

        return result

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            v = dict(vals)
            try:
                if v.get('product_id') and v.get('order_id'):
                    order = self.env['sale.order'].browse(v.get('order_id'))
                    if order.exists() and order.pricelist_id:
                        product = self.env['product.product'].browse(v.get('product_id'))
                        qty = v.get('product_uom_qty') or v.get('product_uom_qty') or v.get('qty', 1.0) or 1.0
                        pricelist = order.pricelist_id
                        pricelist_price = pricelist._get_product_price(product, qty, partner=order.partner_id, uom=product.uom_id)
                        public_price = float(product.lst_price or 0.0)
                        if public_price > pricelist_price and public_price > 0:
                            discount = (public_price - pricelist_price) / public_price * 100
                            v['discount'] = discount
                            v['price_unit'] = public_price
            except Exception:
                # No queremos que un fallo impida la creación de la línea
                pass
            normalized.append(v)
        return super().create(normalized)

