# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    """Transferencias internas: el origen es el almacén permitido del usuario.

    Un usuario con «Almacenes/tiendas permitidos» crea sus traspasos desde su
    propio almacén: se propone por defecto y, si solo tiene uno, no se puede
    cambiar. Las solicitudes a central y el resto de procesos del sistema
    trabajan con sudo y no se ven afectados.
    """

    _inherit = "stock.picking"

    todopintura_origin_locked = fields.Boolean(
        string="Origen fijado al almacén del usuario",
        compute="_compute_todopintura_origin_locked",
    )

    @api.depends_context("uid")
    @api.depends("picking_type_id.code")
    def _compute_todopintura_origin_locked(self):
        locked = len(self.env.user.allowed_warehouse_ids) == 1
        for picking in self:
            picking.todopintura_origin_locked = locked and (
                picking.picking_type_id.code == "internal"
            )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        warehouses = self.env.user.allowed_warehouse_ids
        if not warehouses:
            return values
        picking_type = self.env["stock.picking.type"].browse(
            values.get("picking_type_id")
        )
        if picking_type and picking_type.code != "internal":
            return values
        if picking_type.warehouse_id not in warehouses:
            picking_type = warehouses[:1].int_type_id
            if not picking_type:
                return values
            values["picking_type_id"] = picking_type.id
            values.pop("location_id", None)
        if not values.get("location_id"):
            source = (
                picking_type.default_location_src_id
                or picking_type.warehouse_id.lot_stock_id
            )
            if source:
                values["location_id"] = source.id
        return values

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        pickings._check_todopintura_origin_warehouse()
        return pickings

    def write(self, vals):
        result = super().write(vals)
        if "location_id" in vals or "picking_type_id" in vals:
            self._check_todopintura_origin_warehouse()
        return result

    def _check_todopintura_origin_warehouse(self):
        """No es una constraint: Odoo las ejecuta con sudo y no vería al usuario."""
        warehouses = self.env.user.allowed_warehouse_ids
        if self.env.su or not warehouses:
            return
        for picking in self.filtered(lambda p: p.picking_type_id.code == "internal"):
            origin = picking.location_id.warehouse_id
            if origin and origin not in warehouses:
                raise ValidationError(
                    _(
                        "Solo puede hacer traspasos desde sus almacenes permitidos "
                        "(%(allowed)s); el origen «%(origin)s» no lo es.",
                        allowed=", ".join(warehouses.mapped("name")),
                        origin=picking.location_id.display_name,
                    )
                )
