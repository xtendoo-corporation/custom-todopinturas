# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.fields import Datetime


class StockPicking(models.Model):
    _inherit = "stock.picking"

    tp_min_replenish = fields.Boolean(
        string="Reposición bajo mínimos",
        copy=False,
        help="Traslado generado automáticamente con los productos bajo mínimos del almacén destino.",
    )

    # ---- carga de líneas bajo mínimos ---------------------------------------
    @api.model
    def tp_load_below_min_lines(self, warehouse_id):
        """Deja el traslado de reposición central → almacén con los productos que ahora
        mismo están bajo mínimos en ese almacén.

        - Cantidad a enviar = mínimo − existencias − lo que ya va en camino, sin pasar de
          lo disponible en el almacén central. Sin stock en central no se carga la línea.
        - Reutiliza el traslado de reposición pendiente del almacén: añade las líneas
          nuevas, ajusta las no escaneadas y retira las que ya no están bajo mínimos.
        """
        warehouse = self.env["stock.warehouse"].sudo().browse(warehouse_id)
        summary = {"picking_id": False, "loaded": 0, "skipped_no_stock": 0}
        hub = warehouse._tp_min_get_hub()
        if not warehouse or not hub or hub == warehouse:
            return summary

        picking = self._tp_min_find_picking(hub, warehouse)
        below_min = warehouse._tp_min_below_min_products()
        info = warehouse._tp_min_info(below_min, exclude_pickings=picking)
        quant = self.env["stock.quant"].sudo()
        wanted = {}
        for product in below_min:
            available = quant._get_available_quantity(
                product, hub.lot_stock_id, strict=False
            )
            to_send = min(info[product.id]["to_send"], max(available, 0.0))
            if to_send > 0:
                wanted[product] = to_send
            elif info[product.id]["to_send"] > 0:
                summary["skipped_no_stock"] += 1

        if not picking and wanted:
            picking = self.sudo().create(
                {
                    "picking_type_id": hub.int_type_id.id,
                    "location_id": hub.lot_stock_id.id,
                    "location_dest_id": warehouse.lot_stock_id.id,
                    "origin": _("Reposición bajo mínimos"),
                    "tp_min_replenish": True,
                    "company_id": hub.company_id.id,
                }
            )
        if picking:
            picking._tp_min_sync_moves(wanted)
            summary["picking_id"] = picking.id
        summary["loaded"] = len(wanted)
        return summary

    @api.model
    def _tp_min_find_picking(self, hub, warehouse):
        return self.sudo().search(
            [
                ("tp_min_replenish", "=", True),
                ("location_id", "=", hub.lot_stock_id.id),
                ("location_dest_id", "=", warehouse.lot_stock_id.id),
                ("state", "in", ("draft", "waiting", "confirmed", "assigned")),
            ],
            order="id desc",
            limit=1,
        )

    def _tp_min_sync_moves(self, wanted):
        """Añade, ajusta o retira las líneas de la reposición según `wanted`."""
        self.ensure_one()
        picking = self.sudo()
        existing = {m.product_id: m for m in picking.move_ids.filtered(
            lambda m: m.state not in ("done", "cancel")
        )}
        for product, qty in wanted.items():
            move = existing.get(product)
            if not move:
                picking.env["stock.move"].create(
                    {
                        "picking_id": picking.id,
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "product_uom": product.uom_id.id,
                        "location_id": picking.location_id.id,
                        "location_dest_id": picking.location_dest_id.id,
                        "company_id": picking.company_id.id,
                    }
                )
            elif not move.xt_barcode_scanned_qty and move.product_uom_qty != qty:
                move.product_uom_qty = qty
        stale = picking.move_ids.filtered(
            lambda m: m.product_id not in wanted
            and m.state not in ("done", "cancel")
            and not m.xt_barcode_scanned_qty
        )
        if stale:
            stale._action_cancel()
        if picking.state == "draft" and picking.move_ids.filtered(
            lambda m: m.state == "draft"
        ):
            picking.action_confirm()
        if picking.state in ("confirmed", "waiting"):
            picking.action_assign()

    # ---- datos de la pantalla PDA ---------------------------------------------
    def _tp_min_enrich_lines(self, lines, warehouse):
        """Añade a cada línea de la PDA existencias, mínimo y cantidad a enviar."""
        products = self.env["product.product"].browse(
            [line["product_id"] for line in lines if line.get("product_id")]
        )
        # «A enviar» no cuenta lo que lleva la propia reposición cargada.
        replenish = self.env["stock.picking"].sudo().search(
            [
                ("tp_min_replenish", "=", True),
                ("location_dest_id", "=", warehouse.lot_stock_id.id),
                ("state", "not in", ("done", "cancel")),
            ]
        ) if warehouse else self.env["stock.picking"]
        info = (
            warehouse._tp_min_info(products, exclude_pickings=replenish)
            if warehouse and products
            else {}
        )
        for line in lines:
            data = info.get(line.get("product_id"))
            line["tp_has_min"] = bool(data and data["min"])
            line["tp_dest_qty"] = data["on_hand"] if data else 0.0
            line["tp_min_qty"] = data["min"] if data else 0.0
            line["tp_to_send"] = data["to_send"] if data else 0.0
            line["tp_below_min"] = bool(data and data["below_min"])
        shown = sum(1 for line in lines if line["tp_below_min"])
        return shown, len(lines) - shown

    @api.model
    def _tp_min_banner(self, warehouse, on_screen=0, hidden=0):
        """Aviso de la PDA: bajo mínimos, líneas bajo mínimos en pantalla y las ocultas."""
        if not warehouse:
            return False
        hub = warehouse._tp_min_get_hub()
        if not hub or hub == warehouse:
            return False
        below_min = warehouse._tp_min_below_min_products()
        picking = self._tp_min_find_picking(hub, warehouse)
        info = warehouse._tp_min_info(below_min, exclude_pickings=picking)
        quant = self.env["stock.quant"].sudo()
        skipped = len(
            below_min.filtered(
                lambda p: info[p.id]["to_send"] > 0
                and quant._get_available_quantity(p, hub.lot_stock_id, strict=False) <= 0
            )
        )
        loaded = len(
            picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel"))
        )
        return {
            "warehouse": warehouse.name,
            "below_min": len(below_min),
            "loaded": loaded,
            "on_screen": on_screen,
            "hidden": hidden,
            "skipped_no_stock": skipped,
            "picking": picking.name or False,
            "at": Datetime.to_string(Datetime.now()),
        }

    def action_xt_get_barcode_data(self):
        data = super().action_xt_get_barcode_data()
        warehouse = self.location_dest_id.warehouse_id
        shown, hidden = self._tp_min_enrich_lines(data.get("lines", []), warehouse)
        if self.tp_min_replenish:
            data["tp_banner"] = self._tp_min_banner(warehouse, shown, hidden)
        return data

    @api.model
    def action_xt_get_aggregated_barcode_data(self, location_id):
        data = super().action_xt_get_aggregated_barcode_data(location_id)
        warehouse = self.env["stock.location"].browse(location_id).warehouse_id
        shown, hidden = self._tp_min_enrich_lines(data.get("lines", []), warehouse)
        data["tp_banner"] = self._tp_min_banner(warehouse, shown, hidden)
        return data

    # ---- aviso al escanear un producto que no está bajo mínimos ------------------
    def _tp_min_warn_not_below_min(self, result, product, warehouse):
        if not (result.get("success") and product and warehouse):
            return result
        data = warehouse._tp_min_info(product).get(product.id)
        if data and data["below_min"]:
            return result
        message = _("No está bajo mínimos en %s.", warehouse.name)
        result["message"] = f"{result.get('message') or ''} · {message}".strip(" ·")
        result["excess"] = True  # la PDA lo pinta como aviso
        return result

    def action_xt_process_barcode_scan(self, barcode, force_excess=False):
        result = super().action_xt_process_barcode_scan(barcode, force_excess=force_excess)
        product = self.env["product.product"].search([("barcode", "=", barcode)], limit=1)
        return self._tp_min_warn_not_below_min(
            result, product, self.location_dest_id.warehouse_id
        )

    @api.model
    def action_xt_process_aggregated_barcode_scan(self, location_id, barcode, force_excess=False):
        result = super().action_xt_process_aggregated_barcode_scan(
            location_id, barcode, force_excess=force_excess
        )
        product = self.env["product.product"].search([("barcode", "=", barcode)], limit=1)
        warehouse = self.env["stock.location"].browse(location_id).warehouse_id
        return self._tp_min_warn_not_below_min(result, product, warehouse)
