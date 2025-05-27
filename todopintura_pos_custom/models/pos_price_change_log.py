# models/pos_price_change_log.py
from odoo import models, fields, api

class POSPriceChangeLog(models.Model):
    _name = 'pos.price.change.log'
    _description = 'Registro de cambios de precio en POS'
    _order = 'create_date desc'

    # Solo 'order_reference', 'product_id', 'original_price', 'new_price' y 'date' como requeridos
    order_reference = fields.Char(string='Referencia de pedido', required=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    original_price = fields.Float(string='Precio original', required=True, digits=(16, 2))
    new_price = fields.Float(string='Nuevo precio', required=True, digits=(16, 2))
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now, required=True)

    # Los demás: opcionales
    order_id = fields.Many2one('pos.order', string='Pedido')
    user_id = fields.Many2one('res.users', string='Usuario')
    employee_id = fields.Many2one('hr.employee', string='Empleado')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Completar información adicional si falta
            if not vals.get('user_id'):
                vals['user_id'] = self.env.user.id

            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id

            # Buscar empleado si no está definido
            if not vals.get('employee_id') and vals.get('user_id'):
                employee = self.env['hr.employee'].search([('user_id', '=', vals['user_id'])], limit=1)
                if employee:
                    vals['employee_id'] = employee.id

        return super(POSPriceChangeLog, self).create(vals_list)
