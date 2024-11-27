from odoo import models, fields

class PosCategory(models.Model):
    _inherit = 'pos.category'

    referencia_todopintura = fields.Integer(string="Referencia Todopintura")
