from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class TodopinturasStockCentralRequest(models.Model):
    _name = "todopinturas.stock.central.request"
    _description = "Solicitud a almacén central"
    _order = "request_date desc, id desc"

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nueva"),
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén solicitante",
        required=True,
        default=lambda self: self.env.user.property_warehouse_id,
        index=True,
    )
    warehouse_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación tienda",
        related="warehouse_id.lot_stock_id",
        store=True,
        readonly=True,
    )
    central_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén central",
        required=True,
        default=lambda self: self._default_central_warehouse_id(),
        domain="[('tp_is_central_request_hub', '=', True), ('company_id', '=', company_id)]",
        index=True,
    )
    central_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación central",
        related="central_warehouse_id.lot_stock_id",
        store=True,
        readonly=True,
    )
    request_date = fields.Datetime(
        string="Fecha solicitud",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    requested_by_id = fields.Many2one(
        "res.users",
        string="Solicitado por",
        required=True,
        readonly=True,
        default=lambda self: self.env.user,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("requested", "Solicitada"),
            ("preparing", "Preparando"),
            ("done", "Servida"),
            ("cancel", "Cancelada"),
        ],
        string="Estado",
        required=True,
        default="draft",
        index=True,
    )
    note = fields.Text(string="Observaciones")
    line_ids = fields.One2many(
        "todopinturas.stock.central.request.line",
        "request_id",
        string="Líneas",
        copy=True,
    )
    line_count = fields.Integer(string="Nº líneas", compute="_compute_totals")
    total_qty = fields.Float(string="Cantidad total", compute="_compute_totals")
    total_products = fields.Integer(string="Productos", compute="_compute_totals")
    def _default_central_warehouse_id(self):
        return self.env["stock.warehouse"].search([
            ("company_id", "=", self.env.company.id),
            ("tp_is_central_request_hub", "=", True),
        ], limit=1)

    @api.depends("line_ids.product_qty", "line_ids.product_id")
    def _compute_totals(self):
        for request in self:
            request.line_count = len(request.line_ids)
            request.total_qty = sum(request.line_ids.mapped("product_qty"))
            request.total_products = len(request.line_ids.mapped("product_id"))

    @api.constrains("warehouse_id", "central_warehouse_id", "company_id")
    def _check_warehouses(self):
        for request in self:
            if request.warehouse_id and request.central_warehouse_id and request.warehouse_id == request.central_warehouse_id:
                raise ValidationError(_("El almacén solicitante no puede ser el mismo que el almacén central."))
            if request.warehouse_id.company_id != request.company_id or request.central_warehouse_id.company_id != request.company_id:
                raise ValidationError(_("Los almacenes de la solicitud deben pertenecer a la misma compañía."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nueva")) == _("Nueva"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "todopinturas.stock.central.request"
                ) or _("Nueva")
            vals.setdefault("requested_by_id", self.env.user.id)
            vals.setdefault("company_id", self.env.company.id)
        return super().create(vals_list)

    def _ensure_has_lines(self):
        for request in self:
            if not request.line_ids:
                raise ValidationError(_("Debes añadir al menos una línea antes de solicitar al almacén central."))

    def action_submit(self):
        self._ensure_has_lines()
        self.write({"state": "requested"})

    def action_set_draft(self):
        self.write({"state": "draft"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_mark_preparing(self):
        self.write({"state": "preparing"})

    def action_mark_done(self):
        self.write({"state": "done"})


class TodopinturasStockCentralRequestLine(models.Model):
    _name = "todopinturas.stock.central.request.line"
    _description = "Línea de solicitud a almacén central"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        "todopinturas.stock.central.request",
        string="Solicitud",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="request_id.company_id",
        store=True,
        readonly=True,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        related="request_id.warehouse_id",
        store=True,
        readonly=True,
    )
    central_warehouse_id = fields.Many2one(
        "stock.warehouse",
        related="request_id.central_warehouse_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        related="request_id.state",
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        domain="[('type', '!=', 'service')]",
        index=True,
    )
    description = fields.Char(string="Descripción")
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="UdM",
        related="product_id.uom_id",
        store=True,
        readonly=True,
    )
    product_qty = fields.Float(
        string="Cantidad",
        required=True,
        default=1.0,
        digits="Product Unit of Measure",
    )
    central_available_qty = fields.Float(
        string="Disponible en central",
        compute="_compute_central_available_qty",
        digits="Product Unit of Measure",
    )
    note = fields.Char(string="Nota")

    @api.depends("product_id", "central_warehouse_id")
    def _compute_central_available_qty(self):
        quant_model = self.env["stock.quant"].sudo()
        for line in self:
            if not line.product_id or not line.central_warehouse_id:
                line.central_available_qty = 0.0
                continue
            line.central_available_qty = quant_model._get_available_quantity(
                line.product_id,
                line.central_warehouse_id.lot_stock_id,
                strict=False,
            )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and not line.description:
                line.description = line.product_id.display_name

    @api.constrains("product_qty")
    def _check_product_qty(self):
        for line in self:
            if line.product_qty <= 0:
                raise ValidationError(_("La cantidad solicitada debe ser mayor que cero."))




