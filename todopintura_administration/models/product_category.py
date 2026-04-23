from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    referencia_todopintura = fields.Integer(string="Referencia Todopintura")
