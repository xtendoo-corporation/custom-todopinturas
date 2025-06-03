from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'


    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain += [('name', operator, name)]
        return super()._name_search(name, domain, operator=operator, limit=limit, order=order)

