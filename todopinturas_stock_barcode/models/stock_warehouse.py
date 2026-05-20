from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def _tp_matches_central_request_fallback(self):
        self.ensure_one()
        candidates = {
            (self.name or "").strip().lower(),
            (self.lot_stock_id.name or "").strip().lower(),
            (self.view_location_id.name or "").strip().lower(),
        }
        return "central" in candidates

    tp_is_central_request_hub = fields.Boolean(
        string="Almacén central para solicitudes",
        help="Indica que este almacén actúa como central para las solicitudes de las tiendas.",
    )
    tp_central_request_count = fields.Integer(
        string="Solicitudes relacionadas",
        compute="_compute_tp_central_request_count",
    )

    @api.depends("tp_is_central_request_hub")
    def _compute_tp_central_request_count(self):
        picking_model = self.env["stock.picking"].sudo()
        for warehouse in self:
            domain = [("tp_is_central_request", "=", True)]
            if not warehouse.tp_is_central_request_hub:
                domain.append(("tp_request_destination_warehouse_id", "=", warehouse.id))
            warehouse.tp_central_request_count = picking_model.search_count(domain)

    @api.constrains("tp_is_central_request_hub", "company_id")
    def _check_unique_central_request_hub(self):
        for warehouse in self.filtered("tp_is_central_request_hub"):
            duplicated = self.search_count([
                ("id", "!=", warehouse.id),
                ("company_id", "=", warehouse.company_id.id),
                ("tp_is_central_request_hub", "=", True),
            ])
            if duplicated:
                raise ValidationError(_(
                    "Solo puede existir un almacén central para solicitudes por compañía."
                ))

    @api.model
    def _tp_get_central_request_hub(self, company=None):
        company = company or self.env.company
        configured_hub = self.search([
            ("company_id", "=", company.id),
            ("tp_is_central_request_hub", "=", True),
        ], limit=1)
        if configured_hub:
            return configured_hub
        return self.search([
            ("company_id", "=", company.id),
        ]).filtered(lambda warehouse: warehouse._tp_matches_central_request_fallback())[:1]

    @api.model
    def action_open_tp_central_requests_for_current_user(self):
        user = self.env.user
        warehouse = user.property_warehouse_id if "property_warehouse_id" in user._fields else False
        if warehouse:
            central_hub = warehouse if warehouse.tp_is_central_request_hub else self._tp_get_central_request_hub(warehouse.company_id)
            if not central_hub:
                return {
                    "warning": {
                        "title": _("Solicitudes a central"),
                        "message": _(
                            "No hay ningún almacén marcado o identificable como central para solicitudes en la compañía %s.",
                            warehouse.company_id.display_name,
                        ),
                    }
                }
            return {"action": warehouse.action_view_tp_central_requests()}

        central_hub = self._tp_get_central_request_hub()
        if central_hub:
            return {"action": central_hub.action_view_tp_central_requests()}

        if "property_warehouse_id" not in user._fields:
            return {
                "warning": {
                    "title": _("Solicitudes a central"),
                    "message": _(
                        "No se ha detectado ningún almacén central para solicitudes en la compañía %s.",
                        self.env.company.display_name,
                    ),
                }
            }
        return {
            "warning": {
                "title": _("Solicitudes a central"),
                "message": _(
                    "Tu usuario no tiene un almacén asignado y no se ha detectado ningún almacén central para solicitudes."
                ),
            }
        }

    def action_view_tp_central_requests(self):
        self.ensure_one()
        central_hub = self if self.tp_is_central_request_hub else self._tp_get_central_request_hub(self.company_id)
        action = self.env.ref(
            "todopinturas_stock_barcode.action_todopinturas_central_request"
        ).read()[0]
        action["domain"] = [("tp_is_central_request", "=", True)]
        if not self.tp_is_central_request_hub:
            action["domain"].append(("tp_request_destination_warehouse_id", "=", self.id))
        action["context"] = {
            "default_picking_type_id": central_hub.int_type_id.id if central_hub else False,
            "default_location_id": central_hub.lot_stock_id.id if central_hub else False,
            "default_location_dest_id": self.lot_stock_id.id if not self.tp_is_central_request_hub else False,
            "search_default_group_by_state": 1,
            "search_default_group_by_destination_warehouse": 1,
        }
        return action


