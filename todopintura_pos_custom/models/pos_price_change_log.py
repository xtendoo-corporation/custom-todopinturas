# models/pos_price_change_log.py
from odoo import models, fields, api

class POSPriceChangeLog(models.Model):
    _name = 'pos.price.change.log'
    _description = 'Registro de cambios de precio en POS'
    _order = 'create_date desc'

    order_id = fields.Many2one('pos.order', string='Pedido')
    order_reference = fields.Char(string='Referencia de pedido', required=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    user_id = fields.Many2one('res.users', string='Usuario', required=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado')
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now, required=True)
    original_price = fields.Float(string='Precio original', required=True, digits=(16, 2))
    new_price = fields.Float(string='Nuevo precio', required=True, digits=(16, 2))
    session_id = fields.Many2one('pos.session', string='Sesión POS', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
