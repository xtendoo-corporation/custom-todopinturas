from odoo import models, fields, api
from datetime import date

class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    fecha_inicio = fields.Date(string="Fecha Inicio")
    fecha_fin = fields.Date(string="Fecha Fin")

    @api.depends('fecha_inicio', 'fecha_fin')
    def _compute_active_rule(self):
        """ Activa o desactiva la regla en función de la fecha actual """
        today = date.today()
        for rule in self:
            if rule.fecha_inicio and rule.fecha_fin:
                rule.active = rule.fecha_inicio <= today <= rule.fecha_fin
            else:
                rule.active = True  # Si no hay fechas, siempre está activa

    active = fields.Boolean(string="Activo", compute="_compute_active_rule", store=True)

    @api.model
    def update_orderpoint_status(self):
        """ Revisa las reglas de reabastecimiento y las activa o desactiva según la fecha """
        orderpoints = self.search([])
        for orderpoint in orderpoints:
            orderpoint._compute_active_rule()

    @api.model
    def _create_cron_job(self):
        """ Crea el cron job automáticamente si no existe """
        cron_name = "Actualizar Reglas de Reabastecimiento"
        cron_model = self.env['ir.cron']

        # Buscar si el cron ya existe
        cron = cron_model.search([('name', '=', cron_name)], limit=1)
        if not cron:
            cron_model.create({
                'name': cron_name,
                'model_id': self.env.ref('stock.model_stock_warehouse_orderpoint').id,
                'state': 'code',
                'code': 'stock_warehouse_orderpoint.update_orderpoint_status()',
                'user_id': self.env.ref('base.user_root').id,
                'interval_number': 1,
                'interval_type': 'days',
                'numbercall': -1,
                'active': True,
            })
