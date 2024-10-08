from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    invoice_description = fields.Char(string="Invoice description", help="Invoice description")
