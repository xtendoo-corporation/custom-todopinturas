from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    id_todopinturas = fields.Char(string='ID Todopinturas', help='Identificador interno de Todopinturas para el almacén')


    tp_report_copies = fields.Selection(
        selection=[
            ('2', '2 copias (interna y cliente)'),
            ('3', '3 copias (sin texto, interna y cliente)'),
        ],
        string='Copias de albarán',
        default='2',
        required=True,
        help='Número de copias que se imprimen en cada albarán de este almacén.',
    )
