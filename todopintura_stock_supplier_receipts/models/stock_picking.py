# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, models

PENDING_STATES = ("assigned", "confirmed", "waiting")


class StockPicking(models.Model):
    """PDA de «Entradas» por proveedor.

    La pantalla se abre en modo agregado con `partner_id`; la interfaz manda ese
    proveedor en el contexto (`tp_supplier_id`) de cada llamada y aquí solo se ven y
    se procesan las recepciones pendientes de ese proveedor.
    """

    _inherit = "stock.picking"

    # ---- recepciones pendientes de un proveedor -------------------------------------
    @api.model
    def _tp_sr_get_hub(self):
        return self.env["stock.warehouse"].search(
            [
                ("tp_is_central_request_hub", "=", True),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

    @api.model
    def _tp_sr_base_domain(self):
        return [
            ("picking_type_code", "=", "incoming"),
            ("picking_type_id.warehouse_id.tp_is_central_request_hub", "=", True),
            ("state", "in", PENDING_STATES),
        ]

    @api.model
    def _tp_sr_pickings(self, supplier):
        """Recepciones que estamos esperando recibir de ese proveedor."""
        if not supplier:
            return self.browse()
        return self.search(
            self._tp_sr_base_domain()
            + [("partner_id.commercial_partner_id", "=", supplier.commercial_partner_id.id)]
        )

    @api.model
    def _tp_sr_pending_suppliers(self):
        """Proveedores con alguna recepción pendiente (para el desplegable)."""
        pickings = self.search(self._tp_sr_base_domain() + [("partner_id", "!=", False)])
        return pickings.partner_id.commercial_partner_id

    @api.model
    def _tp_sr_context_supplier(self):
        supplier_id = self.env.context.get("tp_supplier_id")
        return self.env["res.partner"].browse(supplier_id).exists() if supplier_id else False

    # ---- la lógica de mínimos no aplica a las recepciones ---------------------------
    def _tp_min_enrich_lines(self, lines, warehouse):
        if self.env.context.get("tp_supplier_id"):
            for line in lines:
                line.update(
                    tp_manual=False,
                    tp_has_min=False,
                    tp_dest_qty=0.0,
                    tp_min_qty=0.0,
                    tp_to_send=0.0,
                    tp_below_min=True,
                )
            return len(lines), 0
        return super()._tp_min_enrich_lines(lines, warehouse)

    @api.model
    def _tp_min_banner(self, warehouse, on_screen=0, hidden=0):
        if self.env.context.get("tp_supplier_id"):
            return False
        return super()._tp_min_banner(warehouse, on_screen, hidden)

    @api.model
    def _tp_min_add_scanned_line(self, location_id, barcode):
        if self.env.context.get("tp_supplier_id"):
            return False
        return super()._tp_min_add_scanned_line(location_id, barcode)

    def _tp_min_warn_not_below_min(self, result, product, warehouse):
        if self.env.context.get("tp_supplier_id"):
            return result
        return super()._tp_min_warn_not_below_min(result, product, warehouse)

    # ---- datos de la pantalla -------------------------------------------------------
    @api.model
    def action_xt_get_aggregated_barcode_data(self, location_id):
        supplier = self._tp_sr_context_supplier()
        if not supplier:
            return super().action_xt_get_aggregated_barcode_data(location_id)
        pickings = self._tp_sr_pickings(supplier)
        moves = pickings.move_ids.filtered(lambda m: m.state not in ("cancel", "done"))
        products = {}
        for move in moves:
            data = products.setdefault(
                move.product_id.id,
                {
                    "id": move.product_id.id,
                    "product_id": move.product_id.id,
                    "product_name": move.product_id.display_name,
                    "product_barcode": move.product_id.barcode,
                    "picking_name": move.picking_id.name,
                    "qty_done": 0,
                    "qty_demand": 0,
                    "location_id": move.location_id.id,
                    "location_name": move.location_id.display_name,
                    "location_dest_id": move.location_dest_id.id,
                    "location_dest_name": move.location_dest_id.display_name,
                    "move_ids": [],
                },
            )
            data["qty_done"] += move.xt_barcode_scanned_qty
            data["qty_demand"] += move.product_uom_qty
            data["move_ids"].append(move.id)
        location = self.env["stock.location"].browse(location_id)
        return {
            "id": False,
            "name": _("Entradas de %s", supplier.display_name),
            "state": "assigned",
            "picking_type_code": "incoming",
            "location_dest_name": location.display_name,
            "lines": list(products.values()),
            "tp_supplier_banner": {
                "supplier": supplier.display_name,
                "pickings": pickings.mapped("name"),
                "lines": len(products),
            },
        }

    # ---- escaneo ----------------------------------------------------------------
    @api.model
    def action_xt_process_aggregated_barcode_scan(self, location_id, barcode, force_excess=False):
        supplier = self._tp_sr_context_supplier()
        if not supplier:
            return super().action_xt_process_aggregated_barcode_scan(
                location_id, barcode, force_excess=force_excess
            )
        pickings = self._tp_sr_pickings(supplier)
        product = self.env["product.product"].search([("barcode", "=", barcode)], limit=1)
        if not product:
            return {"success": False, "error": _("Producto no encontrado.")}
        moves = pickings.move_ids.filtered(
            lambda m: m.product_id == product and m.state not in ("cancel", "done")
        )
        if not moves:
            return {
                "success": False,
                "error": _(
                    "%(product)s no está pendiente de recibir de %(supplier)s.",
                    product=product.display_name,
                    supplier=supplier.display_name,
                ),
            }
        target_move = moves.filtered(lambda m: m.xt_barcode_scanned_qty < m.product_uom_qty)[:1] or moves[0]
        target = target_move.picking_id
        if force_excess:
            for picking in moves.picking_id:
                picking.write({"xt_barcode_excess_confirmed_product_ids": [(4, product.id)]})
        else:
            excess_error = target._check_barcode_excess_demand(product, 1.0)
            if excess_error:
                return {
                    "success": False,
                    "type": "excess_confirmation",
                    "message": excess_error,
                    "product_name": product.display_name,
                }
        try:
            target._apply_scanned_barcode(barcode, raise_on_error=True, force_excess=force_excess)
            excess_message = target._get_barcode_excess_message(product)
            return {
                "success": True,
                "message": excess_message or _("Producto %s escaneado correctamente.") % product.display_name,
                "excess": bool(excess_message),
            }
        except Exception as error:
            return {"success": False, "error": str(error)}

    # ---- validación ----------------------------------------------------------------
    @api.model
    def action_xt_validate_aggregated_pickings(self, location_id):
        supplier = self._tp_sr_context_supplier()
        if not supplier:
            return super().action_xt_validate_aggregated_pickings(location_id)
        pickings = self._tp_sr_pickings(supplier).filtered(
            lambda p: any(m.xt_barcode_scanned_qty > 0 for m in p.move_ids)
        )
        if not pickings:
            return {"success": False, "error": _("No hay nada escaneado para validar.")}
        validated = self.browse()
        for picking in pickings:
            try:
                result = picking.button_validate()
                if isinstance(result, dict) and result.get("res_model") == "stock.backorder.confirmation":
                    wizard = self.env["stock.backorder.confirmation"].with_context(result["context"]).create({})
                    wizard.process()
                validated |= picking
            except Exception as error:
                return {
                    "success": False,
                    "error": _("Error al validar %(picking)s: %(error)s", picking=picking.name, error=str(error)),
                }
        return {
            "name": _("Entradas validadas"),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("id", "in", validated.ids)],
            "target": "current",
            "context": {},
        }
