from odoo import fields, models


class ResPartner(models.Model):
    """Extensión de res.partner con campos específicos de Todopintura."""

    _inherit = "res.partner"

    todopintura_external_id = fields.Char(
        string="Nº de Cliente (Todopintura)",
        index=True,
        help="Identificador único del cliente en el sistema de Todopintura",
    )

    todopintura_credit_limit = fields.Float(
        string="Límite de Crédito",
        default=0.0,
        help="Límite de crédito específico para este cliente",
    )

    todopintura_discount_fixed = fields.Float(
        string="Descuento Fijo (%)",
        default=0.0,
        help="Descuento fijo aplicable al cliente (%)",
    )

    todopintura_discount_early_payment = fields.Float(
        string="Descuento Pronto Pago (%)",
        default=0.0,
        help="Descuento por pronto pago (%)",
    )

    todopintura_needs_voucher = fields.Selection(
        selection=[("yes", "Sí"), ("no", "No")],
        string="Necesita Vale",
        default="no",
        help="Indica si el cliente necesita vale de compra",
    )

    todopintura_last_sync = fields.Datetime(
        string="Última Sincronización",
        readonly=True,
        help="Fecha y hora de la última importación de datos",
    )

    todopintura_import_log = fields.Text(
        string="Histórico de Importación",
        readonly=True,
        help="Registro de cambios realizados durante las importaciones",
    )
