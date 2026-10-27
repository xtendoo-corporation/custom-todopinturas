from odoo import api, models


class SaleOrderLine(models.Model):
    """Muestra el PVP como precio unitario y la rebaja de la tarifa como descuento.

    La representación se calcula en los mismos métodos que usa Odoo para
    recalcular precio y descuento, de modo que ambos se mantienen coherentes
    cuando cambian el producto, la unidad, la cantidad o la tarifa.
    """

    _inherit = "sale.order.line"

    def _tp_get_public_price(self):
        """PVP del producto en la unidad y moneda de la línea, sin impuestos."""
        self.ensure_one()
        product = self.product_id.with_context(**self._get_product_price_context())
        return product._price_compute(
            "list_price",
            uom=self.product_uom_id,
            currency=self.currency_id,
            company=self.company_id,
            date=self._get_order_date(),
        )[product.id]

    def _tp_get_pricelist_discount(self):
        """Porcentaje que la tarifa rebaja el PVP (0 si no lo rebaja)."""
        self.ensure_one()
        if (
            self.display_type
            or self.combo_item_id
            or not self.product_id
            or not self.product_uom_id
            or not self.order_id.pricelist_id
        ):
            return 0.0
        public_price = self._tp_get_public_price()
        pricelist_price = self._get_pricelist_price()
        if public_price > 0 and public_price > pricelist_price:
            return (public_price - pricelist_price) / public_price * 100
        return 0.0

    def _get_display_price_ignore_combo(self):
        if self._tp_get_pricelist_discount():
            return self._tp_get_public_price()
        return super()._get_display_price_ignore_combo()

    @api.depends("product_id", "product_uom_id", "product_uom_qty")
    def _compute_discount(self):
        super()._compute_discount()
        discount_enabled = self.env[
            "product.pricelist.item"
        ]._is_discount_feature_enabled()
        for line in self:
            if line.combo_item_id or not line.order_id.pricelist_id:
                continue
            discount = line.with_company(line.company_id)._tp_get_pricelist_discount()
            # Sin el grupo de descuentos Odoo no reinicia el descuento al
            # recalcular el precio; hay que hacerlo aquí para no arrastrar
            # un descuento antiguo sobre un precio ya rebajado.
            if discount or not discount_enabled:
                line.discount = discount
