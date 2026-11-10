# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class PriceConsult(models.TransientModel):
    """Consulta de precios: PVP, descuento y precio final de un producto para un cliente.

    Sigue el mismo criterio que pedidos y TPV: el «descuento del cliente» es lo que su
    tarifa rebaja sobre el PVP del producto (ver todopintura_administration).
    """

    _name = "todopintura.price.consult"
    _description = "Consulta de precios por cliente y producto"

    partner_id = fields.Many2one("res.partner", string="Cliente")
    product_id = fields.Many2one(
        "product.product", string="Producto", domain=[("sale_ok", "=", True)]
    )
    ready = fields.Boolean(compute="_compute_prices")
    pricelist_id = fields.Many2one(
        "product.pricelist", string="Tarifa", compute="_compute_prices"
    )
    currency_id = fields.Many2one("res.currency", compute="_compute_prices")
    original_price = fields.Monetary(
        string="Precio original", currency_field="currency_id", compute="_compute_prices"
    )
    discount = fields.Float(string="Descuento del cliente (%)", compute="_compute_prices")
    discount_label = fields.Char(compute="_compute_prices")
    customer_price = fields.Monetary(
        string="Precio para este cliente",
        currency_field="currency_id",
        compute="_compute_prices",
    )

    @api.depends("partner_id", "product_id")
    def _compute_prices(self):
        for wizard in self:
            partner, product = wizard.partner_id, wizard.product_id
            wizard.ready = bool(partner and product)
            wizard.pricelist_id = False
            wizard.currency_id = self.env.company.currency_id
            wizard.original_price = wizard.customer_price = wizard.discount = 0.0
            wizard.discount_label = ""
            if not wizard.ready:
                continue
            # El usuario no necesita acceso a tarifas: se lee solo el resultado.
            partner_s = partner.sudo().with_company(self.env.company)
            pricelist = partner_s.property_product_pricelist
            product_s = product.sudo()
            original = product_s.lst_price
            price = original
            if pricelist:
                price = pricelist._get_product_price(
                    product_s, 1.0, partner=partner_s, uom=product_s.uom_id
                )
                wizard.currency_id = pricelist.currency_id
            wizard.pricelist_id = pricelist
            wizard.original_price = original
            wizard.customer_price = price
            if original > 0 and original > price:
                wizard.discount = (original - price) / original * 100
                number = f"{wizard.discount:.2f}".rstrip("0").rstrip(".").replace(".", ",")
                wizard.discount_label = f"-{number} %"
