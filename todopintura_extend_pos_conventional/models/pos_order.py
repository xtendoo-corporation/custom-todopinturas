# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Ruta",
        domain="[('company_id', 'in', [False, company_id])]",
    )

    def _create_order_picking(self):
        self.ensure_one()
        if self.shipping_date:
            self.sudo().lines._launch_stock_rule_from_pos_order_lines()
        else:
            if self._should_create_picking_real_time():
                picking_type = self.config_id.picking_type_id
                if self.partner_id.property_stock_customer:
                    destination_id = self.partner_id.property_stock_customer.id
                elif not picking_type or not picking_type.default_location_dest_id:
                    destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
                else:
                    destination_id = picking_type.default_location_dest_id.id

                # Agrupar las líneas por route_id
                lines_by_route = {}
                for line in self.lines:
                    route = line.route_id or self.route_id
                    route_id = route.id if route else False
                    if route_id not in lines_by_route:
                        lines_by_route[route_id] = self.env['pos.order.line']
                    lines_by_route[route_id] |= line

                for route_id, group_lines in lines_by_route.items():
                    picking_type = self.config_id.picking_type_id
                    if route_id:
                        route = self.env['stock.route'].browse(route_id)
                        rules = route.rule_ids.filtered(lambda r: r.action == 'pull' and r.picking_type_id)
                        if rules:
                            rule_to_cust = rules.filtered(lambda r: r.location_dest_id.id == destination_id)
                            rule_to_use = rule_to_cust[0] if rule_to_cust else rules[0]
                            picking_type = rule_to_use.picking_type_id

                    pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(
                        destination_id, group_lines, picking_type, self.partner_id
                    )
                    pickings.write({
                        'pos_session_id': self.session_id.id,
                        'pos_order_id': self.id,
                        'origin': self.name,
                    })

    def action_pay_account(self):
        """
        Extiende `pos_conventional` para propagar rutas a sale.order.line.route_id.

        - Si la línea POS tiene ruta, esa manda.
        - Si no, se usa la ruta del pedido POS.
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

        sale_order_lines = []
        for pos_line in self.lines:
            taxes = pos_line.tax_ids_after_fiscal_position or pos_line.tax_ids
            route = pos_line.route_id or self.route_id
            line_vals = {
                "product_id": pos_line.product_id.id,
                "name": pos_line.full_product_name or pos_line.product_id.display_name,
                "product_uom_qty": pos_line.qty,
                "product_uom_id": pos_line.product_id.uom_id.id,
                "price_unit": pos_line.price_unit,
                "discount": pos_line.discount or 0.0,
                "tax_ids": [(6, 0, taxes.ids)] if taxes else False,
                "route_id": route.id if route else False,
            }
            sale_order_lines.append((0, 0, line_vals))

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
            "note": _("Creado desde pedido POS: %s") % self.name,
        }

        if self.company_id:
            sale_order_vals["company_id"] = self.company_id.id

        created_picking = False

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

            for picking in sale_order.picking_ids:
                created_picking = picking
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

        if created_picking:
            report_url = (
                "/report/html/pos_conventional.report_albaran_80mm/%s"
                % created_picking.id
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

    route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Ruta",
        # Dominio dinámico se define en la vista (parent.company_id) para evitar
        # evaluaciones inválidas en el cliente JS.
    )

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            v = dict(vals)
            if not v.get("route_id") and v.get("order_id"):
                order = self.env["pos.order"].browse(v.get("order_id"))
                if order.exists() and order.route_id:
                    v["route_id"] = order.route_id.id
            normalized.append(v)
        return super().create(normalized)

