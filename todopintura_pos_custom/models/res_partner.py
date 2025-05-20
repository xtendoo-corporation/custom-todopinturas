from odoo import models, api, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    voucher = fields.Boolean(string="Vale")
    assigned_persons = fields.Boolean(string="Personas asignadas")
    credit_sale = fields.Boolean(string="Venta a crédito")
    credit_location_id = fields.Many2one(
        'stock.location',
        string="Ubicación Para venta a crédito",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación para ventas a crédito a este cliente"
    )
    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields.extend(['voucher', 'assigned_persons', 'credit_sale', 'credit_location_id'])
        return fields

