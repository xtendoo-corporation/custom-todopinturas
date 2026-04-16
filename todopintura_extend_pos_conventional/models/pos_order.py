# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    origin_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Tienda de venta",
        related="config_id.warehouse_id",
        readonly=True,
    )
    pickup_warehouse_summary = fields.Char(
        string="Resumen tiendas de recogida",
        compute="_compute_pickup_warehouse_summary",
    )
    has_cross_store_pickup_lines = fields.Boolean(
        string="Tiene recogidas en otra tienda",
        compute="_compute_pickup_warehouse_summary",
    )

    @api.depends("config_id.warehouse_id", "lines.pickup_warehouse_id")
    def _compute_pickup_warehouse_summary(self):
        for order in self:
            warehouses = order._get_pickup_warehouses_from_lines()
            order.pickup_warehouse_summary = ", ".join(warehouses.mapped("display_name")) or False
            origin_warehouse = order.origin_warehouse_id or order.config_id.warehouse_id
            order.has_cross_store_pickup_lines = bool(
                warehouses
                and (
                    len(warehouses) > 1
                    or (origin_warehouse and warehouses != origin_warehouse)
                )
            )

    def _get_pickup_warehouse_for_line(self, line):
        self.ensure_one()
        return line.pickup_warehouse_id or self.origin_warehouse_id or self.config_id.warehouse_id

    def _get_pickup_warehouses_from_lines(self):
        self.ensure_one()
        warehouses = self.env["stock.warehouse"]
        for line in self.lines:
            warehouse = self._get_pickup_warehouse_for_line(line)
            if warehouse:
                warehouses |= warehouse
        return warehouses

    def _get_fulfillment_picking_type(self, warehouse):
        self.ensure_one()
        return warehouse.out_type_id or self.config_id.picking_type_id

    def _group_lines_by_pickup_warehouse(self, lines=None):
        self.ensure_one()
        grouped = {}
        lines = lines or self.lines
        empty_lines = self.env["pos.order.line"]
        for line in lines:
            warehouse = self._get_pickup_warehouse_for_line(line)
            key = warehouse.id if warehouse else 0
            if key not in grouped:
                grouped[key] = {
                    "warehouse": warehouse,
                    "lines": empty_lines,
                }
            grouped[key]["lines"] |= line
        return list(grouped.values())

    def _build_sale_note(self):
        self.ensure_one()
        sale_note = _("Creado desde pedido POS: %s") % self.name
        if self.has_cross_store_pickup_lines and self.pickup_warehouse_summary:
            sale_note = "%s\n%s" % (
                sale_note,
                _("Recogida por líneas en: %s") % self.pickup_warehouse_summary,
            )
        return sale_note

    def _prepare_sale_order_line_command(self, pos_line):
        self.ensure_one()
        taxes = pos_line.tax_ids_after_fiscal_position or pos_line.tax_ids
        pickup_warehouse = self._get_pickup_warehouse_for_line(pos_line)
        return (0, 0, {
            "product_id": pos_line.product_id.id,
            "name": pos_line.full_product_name or pos_line.product_id.display_name,
            "product_uom_qty": pos_line.qty,
            "product_uom_id": pos_line.product_id.uom_id.id,
            "price_unit": pos_line.price_unit,
            "discount": pos_line.discount or 0.0,
            "tax_ids": [(6, 0, taxes.ids)] if taxes else False,
            "pickup_warehouse_id": pickup_warehouse.id if pickup_warehouse else False,
        })

    def _split_sale_order_pickings_by_line_warehouse(self, sale_order):
        self.ensure_one()
        active_pickings = sale_order.picking_ids.filtered(lambda p: p.state != "cancel")
        for original_picking in active_pickings:
            pickings_by_warehouse = {}
            moves_to_relocate = []
            original_warehouse = original_picking.picking_type_id.warehouse_id
            for move in original_picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel") and m.sale_line_id):
                target_warehouse = move.sale_line_id.pickup_warehouse_id or original_warehouse or self.origin_warehouse_id
                if not target_warehouse or target_warehouse == original_warehouse:
                    continue
                target_picking_type = self._get_fulfillment_picking_type(target_warehouse)
                target_location = target_picking_type.default_location_src_id or target_warehouse.lot_stock_id
                if target_warehouse.id not in pickings_by_warehouse:
                    pickings_by_warehouse[target_warehouse.id] = original_picking.copy({
                        "move_ids": [],
                        "move_line_ids": [],
                        "picking_type_id": target_picking_type.id,
                        "location_id": target_location.id if target_location else original_picking.location_id.id,
                        "origin": sale_order.name,
                    })
                moves_to_relocate.append((move, pickings_by_warehouse[target_warehouse.id], target_location))

            for move, target_picking, target_location in moves_to_relocate:
                vals = {"picking_id": target_picking.id}
                if target_location:
                    vals["location_id"] = target_location.id
                move.write(vals)

            if moves_to_relocate and not original_picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
                original_picking.action_cancel()

        return sale_order.picking_ids.filtered(lambda p: p.state != "cancel")

    def _create_order_picking(self):
        self.ensure_one()
        if self.picking_ids:
            return
        if self.shipping_date:
            self.sudo().lines._launch_stock_rule_from_pos_order_lines()
        else:
            if self._should_create_picking_real_time():
                for group in self._group_lines_by_pickup_warehouse():
                    picking_type = self._get_fulfillment_picking_type(group["warehouse"])
                    if self.partner_id.property_stock_customer:
                        destination_id = self.partner_id.property_stock_customer.id
                    elif not picking_type or not picking_type.default_location_dest_id:
                        destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
                    else:
                        destination_id = picking_type.default_location_dest_id.id

                    pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(
                        destination_id, group["lines"], picking_type, self.partner_id
                    )
                    pickings.write({
                        'pos_session_id': self.session_id.id,
                        'pos_order_id': self.id,
                        'origin': self.name,
                    })

    def action_pay_account(self):
        """
        Extiende la integración modular de POS Conventional para permitir
        vender en una caja y preparar la entrega desde otra tienda.
        """
        self.ensure_one()

        if self.state != "draft":
            raise UserError(
                _("Solo se pueden convertir a albarán pedidos en estado borrador.")
            )

        if not self.lines:
            raise UserError(
                _("No se puede crear un albarán de un pedido sin líneas de producto.")
            )

        if not self.partner_id:
            raise UserError(_("Debe seleccionar un cliente para crear el albarán."))

        sale_order_lines = [self._prepare_sale_order_line_command(pos_line) for pos_line in self.lines]

        sale_order_vals = {
            "partner_id": self.partner_id.id,
            "partner_invoice_id": self.partner_id.id,
            "partner_shipping_id": self.partner_id.id,
            "pricelist_id": self.pricelist_id.id if self.pricelist_id else False,
            "fiscal_position_id": (
                self.fiscal_position_id.id if self.fiscal_position_id else False
            ),
            "order_line": sale_order_lines,
            "origin": self.name,
            "note": self._build_sale_note(),
            "picking_policy": "direct",
        }

        if self.company_id:
            sale_order_vals["company_id"] = self.company_id.id
        if self.origin_warehouse_id:
            sale_order_vals["warehouse_id"] = self.origin_warehouse_id.id

        created_pickings = self.env["stock.picking"]

        try:
            sale_order = self.env["sale.order"].create(sale_order_vals)
            _logger.info("POS Order %s: Creado sale.order %s", self.name, sale_order.name)

            self.write(
                {
                    "linked_sale_order_id": sale_order.id,
                    "name": sale_order.name,
                    "state": "linked",
                }
            )

            sale_order.action_confirm()
            created_pickings = self._split_sale_order_pickings_by_line_warehouse(sale_order)

            for picking in created_pickings:
                if picking.state == "draft":
                    picking.action_confirm()
                if picking.state != "done":
                    picking.action_assign()
                    for move in picking.move_ids:
                        move.quantity = move.product_uom_qty
                    picking.button_validate()
                    _logger.info(
                        "POS Order %s: Picking %s validado", self.name, picking.name
                    )

        except Exception as e:
            _logger.exception("Error al crear sale.order desde POS: %s", str(e))
            raise UserError(_("Error al crear el albarán: %s") % str(e))

        if created_pickings:
            report_url = (
                "/report/html/pos_conventional_picking_integration.report_albaran_80mm/%s"
                % ",".join(str(picking_id) for picking_id in created_pickings.ids)
            )
            return {
                "type": "ir.actions.client",
                "tag": "pos_conventional_print_iframe",
                "params": {
                    "url": report_url,
                    "next_action": self._get_post_validation_action()
                    or {
                        "type": "ir.actions.act_window",
                        "res_model": "pos.order",
                        "res_id": self.id,
                        "view_mode": "form",
                        "views": [[False, "form"]],
                        "target": "current",
                    },
                },
            }

        next_action = self._get_post_validation_action()
        if next_action:
            return next_action

        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.order",
            "res_id": self.id,
            "view_mode": "form",
            "view_type": "form",
            "target": "current",
        }


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    pickup_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Tienda de recogida",
        help="Tienda en la que se recogerá esta línea del pedido.",
    )

    @api.onchange("order_id")
    def _onchange_order_id_set_pickup_warehouse(self):
        for line in self:
            if line.order_id and not line.pickup_warehouse_id:
                line.pickup_warehouse_id = line.order_id.config_id.warehouse_id

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            new_vals = dict(vals)
            if not new_vals.get("pickup_warehouse_id") and new_vals.get("order_id"):
                order = self.env["pos.order"].browse(new_vals["order_id"])
                if order.exists() and order.config_id.warehouse_id:
                    new_vals["pickup_warehouse_id"] = order.config_id.warehouse_id.id
            normalized.append(new_vals)
        return super().create(normalized)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pickup_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Tienda de recogida",
        help="Tienda desde la que se servirá esta línea de venta creada desde POS.",
    )



