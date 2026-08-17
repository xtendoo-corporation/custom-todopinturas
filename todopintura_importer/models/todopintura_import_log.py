from odoo import fields, models


class TodopinturaImportLog(models.Model):
    """Modelo para registrar los detalles de cada importación."""

    _name = "todopintura.import.log"
    _description = "Registro de Importación Todopintura"
    _order = "create_date DESC"

    import_id = fields.Many2one(
        comodel_name="todopintura.import",
        string="Importación",
        required=True,
        ondelete="cascade",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        ondelete="set null",
    )

    level = fields.Selection(
        selection=[
            ("info", "Información"),
            ("warning", "Advertencia"),
            ("error", "Error"),
        ],
        default="info",
    )

    message = fields.Text(
        string="Mensaje",
        required=True,
    )

    create_date = fields.Datetime(
        string="Fecha",
        readonly=True,
    )
