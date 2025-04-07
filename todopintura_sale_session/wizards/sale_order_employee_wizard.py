from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrderEmployeeWizard(models.TransientModel):
    _name = 'sale.order.employee.wizard'
    _description = 'Asistente para Seleccionar Empleado y PIN'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    pin = fields.Char('PIN', required=True)

    def action_confirm(self):
        employee = self.employee_id
        if employee.pin != self.pin:
            raise UserError('Login fallido. Por favor, inténtelo de nuevo.')

        # Crear el presupuesto (puedes adaptar partner_id, etc.)
        order = self.env['sale.order'].create({
            'user_id': employee.user_id.id,
            'sale_session_id': self.env.context.get('default_sale_session_id'),
            'partner_id': self.env.ref('base.res_partner_1').id,  # puedes cambiar esto por un partner dinámico
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
            'target': 'current',
        }
