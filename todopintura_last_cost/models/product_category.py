from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_cost_method = fields.Selection(
        selection_add=[("last", "Último coste de compra")],
        ondelete={"last": "set default"},
    )
