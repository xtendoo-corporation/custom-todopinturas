from odoo import models, api, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    voucher = fields.Boolean(string="Vale")
    assigned_persons = fields.Boolean(string="Personas asignadas")
    assigned_persons_info = fields.Text(
        string="Información de personas asignadas",
        help="Ingrese detalles sobre las personas asignadas a este cliente"
    )
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
    valued_picking = fields.Boolean(
        string="Mostrar Precios en Albarán",
        default=False,
        help="Si está activado, el albarán mostrará los precios y totales"
    )

    @api.depends('credit_location_id')
    def _compute_credit_location_id_name(self):
        for partner in self:
            partner.credit_location_id_name = partner.credit_location_id.name if partner.credit_location_id else ''

    @api.model
    def _load_pos_data_fields(self, config_id):
        """
        Especifica los campos de res.partner que se cargan en el POS.
        IMPORTANTE: Odoo espera 'fiscal_position_id', no 'property_account_position_id'
        """
        # Obtener los campos base del POS
        fields = super()._load_pos_data_fields(config_id)

        # Asegurarnos de que fiscal_position_id esté incluido
        if 'fiscal_position_id' not in fields:
            fields.append('fiscal_position_id')

        # Agregar nuestros campos personalizados
        custom_fields = [
            'voucher',
            'assigned_persons',
            'assigned_persons_info',
            'credit_sale',
            'credit_location_id',
            'credit_location_id_name',
            'valued_picking'
        ]

        for field in custom_fields:
            if field not in fields:
                fields.append(field)

        return fields

    @api.model
    def check_credit_location_matches_pos(self, partner_id, pos_config_id):
        """
        Permite ventas a crédito si el cliente no tiene ubicación asignada.
        Solo bloquea si tiene una ubicación y es distinta a la de la caja.
        """
        import logging
        _logger = logging.getLogger(__name__)

        _logger.info('=' * 80)
        _logger.info('[CREDIT LOCATION CHECK] Iniciando verificación')
        _logger.info(f'[CREDIT LOCATION CHECK] Partner ID: {partner_id}')
        _logger.info(f'[CREDIT LOCATION CHECK] POS Config ID: {pos_config_id}')

        partner = self.browse(partner_id)
        pos_config = self.env['pos.config'].browse(pos_config_id)

        _logger.info(f'[CREDIT LOCATION CHECK] Partner: {partner.name}')
        _logger.info(f'[CREDIT LOCATION CHECK] POS Config: {pos_config.name}')
        _logger.info(f'[CREDIT LOCATION CHECK] Partner tiene credit_location_id: {bool(partner.credit_location_id)}')

        # Si el cliente NO tiene ubicación de crédito, permitir la venta
        if not partner.credit_location_id:
            _logger.info('[CREDIT LOCATION CHECK] ✅ Cliente SIN ubicación de crédito asignada - PERMITIR VENTA')
            result = {
                'matches': True,
                'error': '',
                'partner_location_name': '',
                'pos_location_name': pos_config.picking_type_id.default_location_src_id.name if pos_config.picking_type_id and pos_config.picking_type_id.default_location_src_id else ''
            }
            _logger.info(f'[CREDIT LOCATION CHECK] Resultado: {result}')
            _logger.info('=' * 80)
            return result

        _logger.info(f'[CREDIT LOCATION CHECK] Partner credit_location_id: {partner.credit_location_id.name} (ID: {partner.credit_location_id.id})')
        _logger.info(f'[CREDIT LOCATION CHECK] POS tiene picking_type_id: {bool(pos_config.picking_type_id)}')

        # Verificar si el POS tiene tipo de operación y ubicación de origen
        if not pos_config.picking_type_id or not pos_config.picking_type_id.default_location_src_id:
            _logger.warning('[CREDIT LOCATION CHECK] ❌ Caja SIN tipo de operación o ubicación de origen')
            result = {
                'matches': False,
                'error': 'Caja sin tipo de operación o ubicación de origen',
                'partner_location_name': partner.credit_location_id.name,
                'pos_location_name': ''
            }
            _logger.info(f'[CREDIT LOCATION CHECK] Resultado: {result}')
            _logger.info('=' * 80)
            return result

        # Comparar las ubicaciones
        pos_location = pos_config.picking_type_id.default_location_src_id
        _logger.info(f'[CREDIT LOCATION CHECK] POS location: {pos_location.name} (ID: {pos_location.id})')

        matches = partner.credit_location_id.id == pos_location.id

        if matches:
            _logger.info('[CREDIT LOCATION CHECK] ✅ Ubicaciones COINCIDEN - PERMITIR VENTA')
        else:
            _logger.warning('[CREDIT LOCATION CHECK] ❌ Ubicaciones NO COINCIDEN - BLOQUEAR VENTA')
            _logger.warning(f'[CREDIT LOCATION CHECK]   - Cliente requiere: {partner.credit_location_id.name} (ID: {partner.credit_location_id.id})')
            _logger.warning(f'[CREDIT LOCATION CHECK]   - POS tiene: {pos_location.name} (ID: {pos_location.id})')

        result = {
            'matches': matches,
            'partner_location_name': partner.credit_location_id.name,
            'pos_location_name': pos_location.name
        }

        _logger.info(f'[CREDIT LOCATION CHECK] Resultado: {result}')
        _logger.info('=' * 80)

        return result


