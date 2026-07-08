from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    delivery_report_print_type = fields.Selection([
        ('standard', 'Estándar'),
        ('valued', 'Valorado'),
    ], string='Impresión de albarán por defecto', default='standard')

    valued_picking = fields.Boolean(
        string='Albarán Valorado',
        compute='_compute_valued_picking',
        store=False,
    )

    @api.depends('delivery_report_print_type')
    def _compute_valued_picking(self):
        for partner in self:
            partner.valued_picking = partner.delivery_report_print_type == 'valued'

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain += [('name', operator, name)]
        return super()._name_search(name, domain, operator=operator, limit=limit, order=order)
