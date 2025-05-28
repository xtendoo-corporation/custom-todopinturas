# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    manual_price = fields.Boolean(
        string='Precio Manual',
        default=False,
        help='Indica si el producto requiere ingreso manual de precio en el TPV'
    )

