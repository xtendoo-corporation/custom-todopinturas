from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    tp_request_source_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén origen solicitud central",
        related="location_id.warehouse_id",
        store=True,
        readonly=True,
        index=True,
    )
    tp_request_destination_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén destino solicitud central",
        related="location_dest_id.warehouse_id",
        store=True,
        readonly=True,
        index=True,
    )
    tp_is_central_request = fields.Boolean(
        string="Solicitud central",
        compute="_compute_tp_is_central_request",
        search="_search_tp_is_central_request",
        index=True,
    )

    @api.depends(
        "tp_request_source_warehouse_id",
        "tp_request_source_warehouse_id.tp_is_central_request_hub",
        "tp_request_source_warehouse_id.name",
        "tp_request_source_warehouse_id.lot_stock_id.name",
        "tp_request_source_warehouse_id.view_location_id.name",
        "location_dest_id",
        "location_dest_id.usage",
    )
    def _compute_tp_is_central_request(self):
        warehouse_model = self.env["stock.warehouse"].sudo()
        central_hubs = {}
        for picking in self:
            company = picking.company_id or self.env.company
            if company.id not in central_hubs:
                central_hubs[company.id] = warehouse_model._tp_get_central_request_hub(company)
            central_hub = central_hubs[company.id]
            picking.tp_is_central_request = bool(
                central_hub
                and picking.tp_request_source_warehouse_id == central_hub
                and picking.location_dest_id
                and picking.location_dest_id.usage != "customer"
            )

    @api.model
    def _search_tp_is_central_request(self, operator, value):
        if operator not in ("=", "!="):
            raise NotImplementedError()

        is_positive = bool(value)
        if operator == "!=":
            is_positive = not is_positive

        warehouse_model = self.env["stock.warehouse"].sudo()
        hub_ids = []
        for company in self.env.companies:
            central_hub = warehouse_model._tp_get_central_request_hub(company)
            if central_hub:
                hub_ids.append(central_hub.id)

        positive_domain = [
            ("tp_request_source_warehouse_id", "in", hub_ids or [0]),
            ("location_dest_id", "!=", False),
            ("location_dest_id.usage", "!=", "customer"),
        ]
        if is_positive:
            return positive_domain

        return [
            "|",
            "|",
            ("tp_request_source_warehouse_id", "not in", hub_ids),
            ("location_dest_id", "=", False),
            ("location_dest_id.usage", "=", "customer"),
        ]

