from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    pos_quick_partner_selectable = fields.Boolean(
        string="Seleccionable al crear cliente rápido",
        default=False,
        help="Si está marcado, esta tarifa se puede asignar a un cliente creado "
        "al vuelo desde un pedido de POS convencional.",
    )
