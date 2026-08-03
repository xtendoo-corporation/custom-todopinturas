from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id', 'product_uom_id', 'quantity')
    def _onchange_product_id_set_pricelist_display(self):
        """When product is changed on an invoice line, if the invoice has a pricelist
        that applies a discount (pricelist price < list price), show the list price
        and set discount percentage so the displayed price is the original and the
        discount reflects the pricelist reduction.
        """
        for line in self:
            try:
                move = line.move_id
                if not line.product_id or not move or not move.pricelist_id:
                    continue
                # quantity as float
                qty = line.quantity or 1.0
                pricelist = move.pricelist_id
                # Get pricelist price (without taxes) in move currency
                pricelist_price = pricelist._get_product_price(
                    line.product_id, qty, partner=move.partner_id, uom=line.product_uom_id
                )
                public_price = float(line.product_id.lst_price or 0.0)
                if public_price > pricelist_price and public_price > 0:
                    # set discount percent and show list price
                    discount = (public_price - pricelist_price) / public_price * 100
                    line.discount = discount
                    line.price_unit = public_price
            except Exception:
                # don't break onchange flow on unexpected errors
                continue

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            v = dict(vals)
            try:
                if v.get('product_id') and v.get('move_id'):
                    move = self.env['account.move'].browse(v.get('move_id'))
                    if move.exists() and move.pricelist_id:
                        product = self.env['product.product'].browse(v.get('product_id'))
                        qty = v.get('quantity') or v.get('qty') or 1.0
                        pricelist = move.pricelist_id
                        pricelist_price = pricelist._get_product_price(product, qty, partner=move.partner_id, uom=product.uom_id)
                        public_price = float(product.lst_price or 0.0)
                        if public_price > pricelist_price and public_price > 0:
                            v['discount'] = (public_price - pricelist_price) / public_price * 100
                            v['price_unit'] = public_price
            except Exception:
                pass
            normalized.append(v)
        return super().create(normalized)

