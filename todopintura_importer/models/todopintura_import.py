import logging
from datetime import datetime

from odoo import fields, models

_logger = logging.getLogger(__name__)


class TodopinturaImport(models.Model):
    """Modelo para gestionar importaciones de clientes desde Todopintura."""

    _name = "todopintura.import"
    _description = "Importación de Clientes Todopintura"
    _order = "create_date DESC"

    name = fields.Char(
        string="Nombre de Importación",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("processing", "Procesando"),
            ("done", "Completada"),
            ("error", "Error"),
        ],
        default="draft",
        readonly=True,
        tracking=True,
    )

    file_name = fields.Char(
        string="Nombre del Archivo",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    import_date = fields.Datetime(
        string="Fecha de Importación",
        default=fields.Datetime.now,
        readonly=True,
    )

    total_records = fields.Integer(
        string="Total de Registros",
        readonly=True,
        help="Total de clientes procesados",
    )

    created_partners = fields.Integer(
        string="Clientes Creados",
        default=0,
        readonly=True,
    )

    updated_partners = fields.Integer(
        string="Clientes Actualizados",
        default=0,
        readonly=True,
    )

    error_count = fields.Integer(
        string="Errores",
        default=0,
        readonly=True,
    )

    log_lines = fields.One2many(
        comodel_name="todopintura.import.log",
        inverse_name="import_id",
        string="Registro de Importación",
        readonly=True,
    )

    notes = fields.Text(
        string="Notas",
        help="Observaciones sobre la importación",
    )

    def _log_message(self, level, message, partner_id=None):
        """
        Registra un mensaje en el histórico de importación.

        Args:
            level: 'info', 'warning', 'error'
            message: Mensaje a registrar
            partner_id: ID del cliente relacionado (opcional)
        """
        self.env["todopintura.import.log"].create(
            {
                "import_id": self.id,
                "level": level,
                "message": message,
                "partner_id": partner_id,
            }
        )

    def process_import(self, records):
        """
        Procesa los registros importados del Excel.

        Args:
            records: Lista de diccionarios con datos de clientes

        Returns:
            dict: Resumen de la importación
        """
        self.state = "processing"
        summary = {"created": 0, "updated": 0, "errors": 0}

        for idx, record in enumerate(records):
            try:
                partner = self._find_or_create_partner(record)
                if partner:
                    if partner.todopintura_last_sync:
                        summary["updated"] += 1
                        self._log_message(
                            "info", f"Cliente actualizado: {partner.name}", partner.id
                        )
                    else:
                        summary["created"] += 1
                        self._log_message(
                            "info", f"Cliente creado: {partner.name}", partner.id
                        )

            except Exception as e:
                summary["errors"] += 1
                self._log_message("error", f"Fila {record.get('row_number')}: {str(e)}")
                _logger.error(f"Error processing record {idx}: {e}")

        self.total_records = len(records)
        self.created_partners = summary["created"]
        self.updated_partners = summary["updated"]
        self.error_count = summary["errors"]
        self.state = "done" if summary["errors"] == 0 else "error"

        return summary

    def _find_or_create_partner(self, record):
        """
        Busca un cliente existente o crea uno nuevo.

        Estrategia:
        1. Buscar por todopintura_external_id
        2. Si no existe, buscar por VAT
        3. Si no existe, crear nuevo

        Args:
            record: Diccionario con datos del cliente

        Returns:
            res.partner: Cliente encontrado o creado
        """
        ResPartner = self.env["res.partner"]
        external_id = record.get("external_id")
        vat = record.get("vat")

        # Búsqueda 1: Por external_id
        partner = ResPartner.search(
            [("todopintura_external_id", "=", external_id)], limit=1
        )

        if not partner and vat:
            # Búsqueda 2: Por VAT
            partner = ResPartner.search([("vat", "=", vat)], limit=1)

        if partner:
            # Actualizar datos del cliente existente
            self._update_partner(partner, record)
        else:
            # Crear nuevo cliente
            partner = self._create_partner(record)

        return partner

    def _create_partner(self, record):
        """
        Crea un nuevo cliente en Odoo.

        Args:
            record: Diccionario con datos del cliente

        Returns:
            res.partner: Cliente creado
        """
        ResPartner = self.env["res.partner"]

        partner_data = {
            "name": record.get("name"),
            "todopintura_external_id": record.get("external_id"),
            "street": record.get("street"),
            "zip": record.get("zip"),
            "phone": record.get("phone"),
            "mobile": record.get("mobile"),
            "vat": record.get("vat"),
            "email": record.get("email"),
            "todopintura_credit_limit": record.get("credit_limit", 0.0),
            "todopintura_discount_fixed": record.get("discount_fixed", 0.0),
            "todopintura_discount_early_payment": record.get(
                "discount_early_payment", 0.0
            ),
            "todopintura_needs_voucher": record.get("needs_voucher", "no"),
            "todopintura_last_sync": datetime.now(),
        }

        # Agregar comentario si existe
        if record.get("comment"):
            partner_data["comment"] = record.get("comment")

        # Mapear payment term si existe
        payment_term_name = record.get("payment_term")
        if payment_term_name:
            payment_term = self.env["account.payment.term"].search(
                [("name", "ilike", payment_term_name)], limit=1
            )
            if payment_term:
                partner_data["property_payment_term_id"] = payment_term.id

        partner = ResPartner.create(partner_data)
        return partner

    def _update_partner(self, partner, record):
        """
        Actualiza los datos de un cliente existente.

        Args:
            partner: Instancia de res.partner
            record: Diccionario con nuevos datos
        """
        update_data = {}

        # Campos que se actualizan
        updateable_fields = {
            "street": "street",
            "zip": "zip",
            "phone": "phone",
            "mobile": "mobile",
            "email": "email",
            "credit_limit": "todopintura_credit_limit",
            "discount_fixed": "todopintura_discount_fixed",
            "discount_early_payment": "todopintura_discount_early_payment",
            "needs_voucher": "todopintura_needs_voucher",
        }

        for source_key, target_field in updateable_fields.items():
            value = record.get(source_key)
            if value:
                update_data[target_field] = value

        # VAT solo si no existe
        if not partner.vat and record.get("vat"):
            update_data["vat"] = record.get("vat")

        # Comentario: concatenar con el anterior
        if record.get("comment"):
            existing_comment = partner.comment or ""
            new_comment = record.get("comment")
            if existing_comment and new_comment not in existing_comment:
                update_data["comment"] = f"{existing_comment}\n---\n{new_comment}"
            elif not existing_comment:
                update_data["comment"] = new_comment

        # Actualizar fecha de sincronización
        update_data["todopintura_last_sync"] = datetime.now()

        if update_data:
            partner.write(update_data)
