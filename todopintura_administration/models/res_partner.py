from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    assigned_person_ids = fields.One2many('res.partner', 'parent_id', string="Personas asignadas")
    # Campo para seleccionar múltiples contactos a la vez
    contact_to_assign_ids = fields.Many2many('res.partner', string="Contactos a asignar",
                                             domain=[('parent_id', '=', False)],
                                             relation='res_partner_assign_rel',
                                             column1='partner_id', column2='assigned_id')

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain += [('name', operator, name)]
        return super()._name_search(name, domain, operator=operator, limit=limit, order=order)

    def action_add_existing_contacts(self):
        """Añade varios contactos seleccionados como personas asignadas"""
        for partner in self:
            if partner.contact_to_assign_ids:
                # Filtrar para evitar auto-asignación
                contacts_to_assign = partner.contact_to_assign_ids.filtered(lambda c: c.id != partner.id)
                if contacts_to_assign:
                    contacts_to_assign.write({'parent_id': partner.id})
                # Limpiar la selección después de asignar
                partner.contact_to_assign_ids = [(5, 0, 0)]
        return True
