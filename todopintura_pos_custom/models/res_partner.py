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
    credit_location_id_name = fields.Char(
        string="Nombre de la Ubicación Para venta a crédito",
        compute='_compute_credit_location_id_name',
        store=True
    )

    @api.depends('credit_location_id')
    def _compute_credit_location_id_name(self):
        for partner in self:
            partner.credit_location_id_name = partner.credit_location_id.name if partner.credit_location_id else ''

    @api.model
    def _load_pos_data_fields(self, config_id):
        print("Loading POS data fields for ResPartner")
        fields = super()._load_pos_data_fields(config_id)
        fields.extend(['voucher', 'assigned_persons', 'credit_sale', 'credit_location_id','credit_location_id_name'])
        print("Fields loaded:", fields)
        return fields

    @api.model
    def check_credit_location_matches_pos(self, partner_id, pos_config_id):
        """
        Verifica si la ubicación de crédito del cliente coincide con la ubicación
        de origen del tipo de operación de la caja POS.
        """
        partner = self.browse(partner_id)
        pos_config = self.env['pos.config'].browse(pos_config_id)

        # Verificar si el cliente tiene una ubicación de crédito definida
        if not partner.credit_location_id:
            return {
                'matches': False,
                'error': 'Cliente sin ubicación de crédito definida',
                'partner_location_name': '',
                'pos_location_name': pos_config.picking_type_id.default_location_src_id.name if pos_config.picking_type_id and pos_config.picking_type_id.default_location_src_id else ''
            }

        # Verificar si el POS tiene tipo de operación y ubicación de origen
        if not pos_config.picking_type_id or not pos_config.picking_type_id.default_location_src_id:
            return {
                'matches': False,
                'error': 'Caja sin tipo de operación o ubicación de origen',
                'partner_location_name': partner.credit_location_id.name,
                'pos_location_name': ''
            }

        # Comparar las ubicaciones
        pos_location = pos_config.picking_type_id.default_location_src_id
        matches = partner.credit_location_id.id == pos_location.id

        return {
            'matches': matches,
            'partner_location_name': partner.credit_location_id.name,
            'pos_location_name': pos_location.name
        }
