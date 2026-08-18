from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    referencia_todopintura = fields.Integer(string="Referencia Todopintura")
