# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockBarcodeSupplierWizard(models.TransientModel):
    """«Entradas»: se pregunta el proveedor antes de abrir la PDA de recepción."""

    _name = "stock.barcode.supplier.wizard"
    _description = "Seleccionar proveedor para las entradas"

    available_partner_ids = fields.Many2many(
        "res.partner",
        compute="_compute_available_partner_ids",
        string="Proveedores con entradas pendientes",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Proveedor",
        required=True,
        domain="[('id', 'in', available_partner_ids)]",
    )
    pending_count = fields.Integer(compute="_compute_pending_count")

    @api.depends_context("uid")
    def _compute_available_partner_ids(self):
        partners = self.env["stock.picking"]._tp_sr_pending_suppliers()
        for wizard in self:
            wizard.available_partner_ids = partners

    @api.depends("partner_id")
    def _compute_pending_count(self):
        for wizard in self:
            wizard.pending_count = (
                len(self.env["stock.picking"]._tp_sr_pickings(wizard.partner_id))
                if wizard.partner_id
                else 0
            )

    def action_continue(self):
        self.ensure_one()
        hub = self.env["stock.picking"]._tp_sr_get_hub()
        if not hub:
            raise UserError(_("No hay un almacén central configurado para las entradas."))
        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_stock_barcode_client_action",
            "name": _("Entradas de %s", self.partner_id.display_name),
            "target": "fullscreen",
            "params": {
                "model": "stock.picking",
                "location_id": hub.lot_stock_id.id,
                "warehouse_id": hub.id,
                "partner_id": self.partner_id.commercial_partner_id.id,
                "mode": "aggregated",
            },
        }

    def action_open_list(self):
        """Listado clásico de entradas (todas, sin filtrar por proveedor)."""
        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_stock_barcode_picking_list",
            "name": _("Entradas"),
            "params": {
                "domain": [
                    ("picking_type_code", "=", "incoming"),
                    ("picking_type_id.warehouse_id.tp_is_central_request_hub", "=", True),
                ]
            },
        }
