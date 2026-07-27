from odoo import api, models
from odoo.exceptions import AccessError
from odoo.tools.translate import _
from odoo.tools import float_compare


class PosOrderLinePermissions(models.Model):
    _inherit = 'pos.order.line'

    def write(self, vals):
        # Campos de precio que queremos proteger
        protected_fields = {'price_unit', 'discount'}
        # Permitir cambios de precio si el contexto indica que provienen de una
        # actualización de pricelist u operación autorizada por el sistema.
        is_pricelist_update = bool(
            self.env.context.get('pricelist_update')
            or self.env.context.get('from_pricelist')
            or self.env.context.get('allow_price_update')
        )
        if any(f in vals for f in protected_fields) and not is_pricelist_update:
            # Si el usuario tiene permiso, permitir
            if getattr(self.env.user, 'pos_can_edit_price', False):
                return super(PosOrderLinePermissions, self).write(vals)

            # Si no tiene permiso, permitimos la modificación sólo si el nuevo
            # precio/discount coincide con el calculado por la pricelist del pedido
            # (es decir, viene de una recomputación automática).
            allow_if_matches_pricelist = True
            if 'price_unit' in vals or 'discount' in vals:
                for line in self:
                    new_price = vals.get('price_unit', line.price_unit)
                    new_discount = vals.get('discount', line.discount)
                    order = line.order_id
                    pricelist = order.pricelist_id if order and order.pricelist_id else None
                    if not pricelist or not line.product_id:
                        allow_if_matches_pricelist = False
                        break
                    product = line.product_id
                    qty = vals.get('qty', line.qty) or 1.0
                    # Precio esperado según la pricelist (precio neto)
                    expected_price = pricelist._get_product_price(product, qty, partner=order.partner_id, uom=product.uom_id)
                    # Valores preparados por la propia lógica del pedido (puede devolver price_unit público + descuento)
                    prepared = order._prepare_order_line_vals(product, qty) if order else None
                    expected_discount = prepared['discount'] if prepared else 0.0
                    public_price = product.lst_price
                    currency = order.currency_id if order and order.currency_id else (order.company_id.currency_id if order and order.company_id else None)
                    rounding = currency.rounding if currency else 0.0001

                    # Aceptar la modificación si coincide con el precio de pricelist
                    if 'price_unit' in vals and float_compare(expected_price, float(new_price), precision_rounding=rounding) == 0:
                        continue

                    # O aceptar si coincide el descuento calculado por la lógica de pricelist
                    if 'discount' in vals and float_compare(expected_discount, float(new_discount), precision_rounding=rounding) == 0:
                        continue

                    # O aceptar si vienen representados como (price_unit == public_price) + descuento == expected_discount
                    if (
                        'price_unit' in vals
                        and float_compare(float(new_price), public_price, precision_rounding=rounding) == 0
                        and 'discount' in vals
                        and float_compare(expected_discount, float(new_discount), precision_rounding=rounding) == 0
                    ):
                        continue

                    allow_if_matches_pricelist = False
                    break

            if not allow_if_matches_pricelist:
                raise AccessError(_('No tiene permisos para cambiar precios en TPV.'))

        return super(PosOrderLinePermissions, self).write(vals)

    @classmethod
    def _map_vals_list_has_protected(cls, vals_list):
        protected_fields = {'price_unit', 'discount'}
        for vals in vals_list:
            if any(f in vals for f in protected_fields):
                return True
        return False

    def create(self, vals_list):
        # Si se intenta crear líneas con precio distinto y el usuario no tiene permiso, denegar
        is_pricelist_update = bool(
            self.env.context.get('pricelist_update')
            or self.env.context.get('from_pricelist')
            or self.env.context.get('allow_price_update')
        )
        if self._map_vals_list_has_protected(vals_list) and not is_pricelist_update:
            if getattr(self.env.user, 'pos_can_edit_price', False):
                return super(PosOrderLinePermissions, self).create(vals_list)

            for vals in vals_list:
                product_id = vals.get('product_id')
                order_id = vals.get('order_id')
                if not product_id or not order_id:
                    raise AccessError(_('No tiene permisos para crear líneas con precio modificado en TPV.'))
                product = self.env['product.product'].browse(product_id)
                order = self.env['pos.order'].browse(order_id)
                pricelist = order.pricelist_id if order and order.pricelist_id else None
                if not pricelist:
                    raise AccessError(_('No tiene permisos para crear líneas con precio modificado en TPV.'))
                qty = vals.get('qty', 1.0)
                expected_price = pricelist._get_product_price(product, qty, partner=order.partner_id, uom=product.uom_id)
                prepared = order._prepare_order_line_vals(product, qty) if order else None
                expected_discount = prepared['discount'] if prepared else 0.0
                public_price = product.lst_price
                rounding = (order.currency_id.rounding if order and order.currency_id else (order.company_id.currency_id.rounding if order and order.company_id else 0.0001))

                # Aceptar si el precio coincide con el calculado por la pricelist
                if 'price_unit' in vals and float_compare(expected_price, float(vals.get('price_unit')), precision_rounding=rounding) == 0:
                    pass
                # O aceptar si el descuento coincide con el esperado
                elif 'discount' in vals and float_compare(expected_discount, float(vals.get('discount')), precision_rounding=rounding) == 0:
                    pass
                # O aceptar la representación (price_unit == public_price) + descuento == expected_discount
                elif (
                    'price_unit' in vals
                    and float_compare(float(vals.get('price_unit')), public_price, precision_rounding=rounding) == 0
                    and 'discount' in vals
                    and float_compare(expected_discount, float(vals.get('discount')), precision_rounding=rounding) == 0
                ):
                    pass
                else:
                    raise AccessError(_('No tiene permisos para crear líneas con precio modificado en TPV.'))

        return super(PosOrderLinePermissions, self).create(vals_list)

