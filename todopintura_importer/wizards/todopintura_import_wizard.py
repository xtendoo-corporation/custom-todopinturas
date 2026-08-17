import base64
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..utils.excel_parser import TodopinturaExcelParser

_logger = logging.getLogger(__name__)


class TodopinturaImportWizard(models.TransientModel):
    """Wizard para importar clientes desde archivos Excel de Todopintura."""

    _name = "todopintura.import.wizard"
    _description = "Asistente de Importación Todopintura"

    file = fields.Binary(
        string="Archivo Excel",
        required=True,
        help="Seleccionar archivo UMACLI.xlsx de Todopintura",
    )

    file_name = fields.Char(
        string="Nombre del Archivo",
        required=True,
    )

    preview = fields.Text(
        string="Vista Previa",
        readonly=True,
        compute="_compute_preview",
    )

    total_records = fields.Integer(
        string="Total de Registros",
        readonly=True,
        compute="_compute_preview",
    )

    has_errors = fields.Boolean(
        string="¿Tiene Errores?",
        readonly=True,
        compute="_compute_preview",
    )

    error_messages = fields.Text(
        string="Mensajes de Error",
        readonly=True,
        compute="_compute_preview",
    )

    warning_messages = fields.Text(
        string="Advertencias",
        readonly=True,
        compute="_compute_preview",
    )

    @api.depends("file", "file_name")
    def _compute_preview(self):
        """Calcula la vista previa y valida el archivo."""
        for record in self:
            if not record.file:
                record.preview = ""
                record.total_records = 0
                record.has_errors = False
                record.error_messages = ""
                record.warning_messages = ""
                continue

            try:
                file_content = base64.b64decode(record.file)
                parser = TodopinturaExcelParser(file_content)
                records = parser.parse()

                summary = parser.get_summary()
                record.total_records = summary["total_records"]
                record.has_errors = not summary["success"]
                record.error_messages = (
                    "\n".join(summary["errors"]) if summary["errors"] else ""
                )
                record.warning_messages = (
                    "\n".join(summary["warnings"]) if summary["warnings"] else ""
                )

                # Generar vista previa
                if records:
                    preview_lines = [f"✓ Se procesarán {len(records)} clientes\n"]
                    for i, rec in enumerate(records[:5], 1):
                        preview_lines.append(
                            f"  {i}. {rec.get('external_id')} - {rec.get('name')}"
                        )
                    if len(records) > 5:
                        preview_lines.append(f"  ... y {len(records) - 5} más")
                    record.preview = "\n".join(preview_lines)
                else:
                    record.preview = (
                        "⚠ No se encontraron registros válidos en el archivo"
                    )

            except Exception as e:
                record.preview = f"❌ Error al procesar el archivo: {str(e)}"
                record.has_errors = True
                record.error_messages = str(e)
                record.total_records = 0

    def action_import(self):
        """
        Ejecuta la importación de clientes.

        Returns:
            dict: Acción para mostrar el resultado de la importación
        """
        self.ensure_one()

        if not self.file:
            raise UserError(
                self.env._(
                    "Debes seleccionar un archivo Excel para continuar."
                )
            )

        if self.has_errors:
            raise UserError(
                self.env._(
                    "El archivo contiene errores y no puede ser importado:\n\n%s"
                )
                % self.error_messages
            )

        try:
            # Decodificar archivo
            file_content = base64.b64decode(self.file)

            # Parsear Excel
            parser = TodopinturaExcelParser(file_content)
            records = parser.parse()

            if not records:
                raise UserError(
                    self.env._(
                        "No se encontraron registros válidos en el archivo."
                    )
                    + "\n\n"
                    + "\n".join(parser.get_summary()["errors"])
                )

            # Crear registro de importación
            import_record = self.env["todopintura.import"].create(
                {
                    "name": f"Importación {self.file_name}",
                    "file_name": self.file_name,
                }
            )

            # Procesar registros
            import_record.process_import(records)

            # Mostrar resultado
            return {
                "type": "ir.actions.act_window",
                "res_model": "todopintura.import",
                "res_id": import_record.id,
                "view_mode": "form",
                "target": "current",
            }

        except Exception as e:
            _logger.error(f"Error during import: {e}")
            raise UserError(
                self.env._(
                    f"Error durante la importación:\n\n{str(e)}"
                )
            ) from e
