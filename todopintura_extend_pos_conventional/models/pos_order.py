# -*- coding: utf-8 -*-

import logging
import json

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    _CONVENTIONAL_PAID_PRINTABLE_STATES = ("paid", "done", "invoiced")

    def _normalize_conventional_payment_method(self, payment_method=None):
        self.ensure_one()
        if not payment_method:
            return self.env["pos.payment.method"]
        if hasattr(payment_method, "exists"):
            return payment_method.exists()
        try:
            return self.env["pos.payment.method"].browse(int(payment_method)).exists()
        except (TypeError, ValueError):
            return self.env["pos.payment.method"]

    def _get_default_conventional_cash_payment_method(self):
        self.ensure_one()
        cash_method = self.config_id.payment_method_ids.filtered("is_cash_count")[:1]
        if not cash_method:
            cash_method = self.config_id.payment_method_ids.filtered(
                lambda payment_method: payment_method.journal_id.type == "cash"
            )[:1]
        return cash_method

    def _get_credit_cashier_warning_message(
        self, payment_method=None, for_partner_selection=False
    ):
        self.ensure_one()
        if self.env.context.get("skip_credit_cashier_warning"):
            return False
        if self.state != "draft" or not self.partner_id:
            return False
        if not for_partner_selection and self._get_credit_amount_to_check() <= 0:
            return False

        payment_method = self._normalize_conventional_payment_method(payment_method)
        if payment_method and payment_method.type == "pay_later":
            return False

        policy = self._get_conventional_credit_policy_data()
        if not (policy["credit_sale_allowed"] and policy["location_allowed"]):
            return False

        return self.partner_credit_cashier_warning or _(
            "ATENCIÓN: este cliente tiene crédito habilitado en esta caja. "
            "Si la venta debe ir a cuenta, utilice el método 'Pago Cuenta de cliente' "
            "para evitar cobrarla por efectivo o tarjeta por error."
        )

    def _should_show_credit_cashier_warning(self, payment_method=None):
        self.ensure_one()
        return bool(self._get_credit_cashier_warning_message(payment_method=payment_method))

    def _open_credit_cashier_warning_wizard(
        self,
        payment_method=None,
        resume_action=None,
        payment_wizard=None,
        revert_partner_id=None,
        warning_message=None,
    ):
        self.ensure_one()
        action = self.env.ref(
            "todopintura_extend_pos_conventional.action_pos_conventional_credit_cashier_warning_wizard"
        ).read()[0]
        payment_method = self._normalize_conventional_payment_method(payment_method)
        warning_message = warning_message or self._get_credit_cashier_warning_message(
            payment_method=payment_method,
            for_partner_selection=resume_action == "partner_selected",
        )
        action["context"] = {
            "default_order_id": self.id,
            "default_payment_method_id": payment_method.id if payment_method else False,
            "default_payment_wizard_id": payment_wizard.id if payment_wizard else False,
            "default_resume_action": resume_action,
            "default_revert_partner_id": revert_partner_id,
            "default_warning_message": warning_message,
        }
        return action

    def action_open_partner_credit_cashier_warning(self, previous_partner_id=False):
        self.ensure_one()
        warning_message = self._get_credit_cashier_warning_message(
            for_partner_selection=True,
        )
        if not warning_message:
            return False
        return self._open_credit_cashier_warning_wizard(
            resume_action="partner_selected",
            revert_partner_id=previous_partner_id or False,
            warning_message=warning_message,
        )

    def _process_conventional_pay_later(self, payment_method=None, amount=None):
        self.ensure_one()
        reset_vals = {}
        if "to_invoice" in self._fields:
            reset_vals["to_invoice"] = False
        if "is_l10n_es_simplified_invoice" in self._fields:
            reset_vals["is_l10n_es_simplified_invoice"] = False
        if reset_vals:
            self.with_context(skip_completeness_check=True).write(reset_vals)
        return self.with_context(skip_conventional_picking_print=True).action_pay_account()

    def _get_conventional_post_validation_action_without_print(self):
        self.ensure_one()
        action = self._get_post_validation_action()
        if isinstance(action, dict) and action.get("tag") in {
            "pos_conventional_print_receipt_client",
            "pos_conventional_print_iframe",
            "pos_conventional_print_receipt_window",
        }:
            params = action.get("params") or {}
            next_action = params.get("next_action")
            if next_action:
                return next_action
        return action

    def action_pos_convention_pay_with_method(self, payment_method_id):
        self.ensure_one()

        payment_method = payment_method_id
        if not hasattr(payment_method, "id"):
            try:
                payment_method = self.env["pos.payment.method"].browse(int(payment_method_id))
            except (TypeError, ValueError):
                return super().action_pos_convention_pay_with_method(payment_method_id)

        if payment_method and payment_method.exists() and payment_method.type == "pay_later":
            amount_due = self.amount_total - self.amount_paid
            if amount_due <= 0:
                raise UserError(_("The order is already fully paid."))

            wizard = self.env["pos.make.payment"].with_context(active_id=self.id).create({
                "amount": amount_due,
                "payment_method_id": payment_method.id,
            })
            return wizard.check()

        return super().action_pos_convention_pay_with_method(payment_method_id)

    def action_pay_cash(self):
        self.ensure_one()
        return super().action_pay_cash()

    origin_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Tienda de venta",
        related="config_id.warehouse_id",
        readonly=True,
    )
    is_a4_invoice = fields.Boolean(
        string="Factura A4",
        default=False,
    )
    pickup_warehouse_summary = fields.Char(
        string="Resumen tiendas de recogida",
        compute="_compute_pickup_warehouse_summary",
    )
    has_cross_store_pickup_lines = fields.Boolean(
        string="Tiene recogidas en otra tienda",
        compute="_compute_pickup_warehouse_summary",
    )
    current_credit_location_name = fields.Char(
        string="Ubicación actual de cobro/crédito",
        compute="_compute_partner_credit_policy",
    )
    partner_credit_location_names = fields.Char(
        string="Ubicaciones permitidas para crédito",
        compute="_compute_partner_credit_policy",
    )
    partner_pickup_persons_display = fields.Text(
        string="Autorizados de recogida",
        compute="_compute_partner_credit_policy",
    )
    partner_pickup_persons_inline = fields.Char(
        string="Autorizados de recogida (resumen)",
        compute="_compute_partner_credit_policy",
    )
    partner_requires_voucher = fields.Boolean(
        string="Necesita vale",
        compute="_compute_partner_credit_policy",
    )
    partner_voucher_reference = fields.Char(
        string="Código / documento del vale",
        compute="_compute_partner_credit_policy",
    )
    partner_current_total_due = fields.Monetary(
        string="Deuda POS pendiente",
        compute="_compute_partner_credit_policy",
        currency_field="currency_id",
    )
    partner_credit_limit_amount = fields.Monetary(
        string="Límite de riesgo",
        compute="_compute_partner_credit_policy",
        currency_field="currency_id",
    )
    partner_total_due_after_order = fields.Monetary(
        string="Deuda tras el pedido",
        compute="_compute_partner_credit_policy",
        currency_field="currency_id",
    )
    partner_credit_warning_message = fields.Text(
        string="Aviso de crédito",
        compute="_compute_partner_credit_policy",
    )
    partner_credit_available = fields.Boolean(
        string="Cliente con crédito disponible",
        compute="_compute_partner_credit_policy",
    )
    partner_credit_cashier_warning = fields.Text(
        string="Aviso visible para caja",
        compute="_compute_partner_credit_policy",
    )
    credit_limit_override_approved = fields.Boolean(
        string="Override de límite aprobado",
        readonly=True,
        copy=False,
    )
    credit_limit_override_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Override aprobado por",
        readonly=True,
        copy=False,
    )
    credit_limit_override_date = fields.Datetime(
        string="Fecha override límite",
        readonly=True,
        copy=False,
    )
    can_print_paid_albaran = fields.Boolean(
        string="Puede imprimir albarán pagado",
        compute="_compute_conventional_paid_print_buttons",
    )
    can_print_paid_invoice = fields.Boolean(
        string="Puede imprimir factura pagada",
        compute="_compute_conventional_paid_print_buttons",
    )

    @api.depends(
        "state",
        "show_albaran_button",
        "picking_ids",
        "picking_ids.state",
        "linked_sale_order_id",
        "linked_sale_order_id.picking_ids",
        "linked_sale_order_id.picking_ids.state",
        "account_move",
    )
    def _compute_conventional_paid_print_buttons(self):
        for order in self:
            can_print_albaran = bool(
                order.state in self._CONVENTIONAL_PAID_PRINTABLE_STATES
                and order._get_conventional_reprint_pickings()
            )
            order.can_print_paid_albaran = can_print_albaran
            order.can_print_paid_invoice = bool(
                order.state in self._CONVENTIONAL_PAID_PRINTABLE_STATES
                and order.account_move
            )

    def _get_conventional_reprint_pickings(self):
        self.ensure_one()
        pickings = (self.picking_ids | self.linked_sale_order_id.picking_ids).filtered(
            lambda picking: picking.state != "cancel"
        )
        return pickings.sorted(lambda picking: (picking.date_done or picking.scheduled_date or picking.create_date, picking.id), reverse=True)

    def _ensure_conventional_paid_printable_order(self):
        self.ensure_one()
        if self.state not in self._CONVENTIONAL_PAID_PRINTABLE_STATES:
            raise UserError(
                _("Solo se pueden reimprimir documentos en pedidos POS ya pagados o cerrados.")
            )

    def action_print_paid_albaran(self):
        self.ensure_one()
        self._ensure_conventional_paid_printable_order()
        pickings = self._get_conventional_reprint_pickings()
        if not pickings:
            raise UserError(_("Este pedido no tiene albaranes disponibles para imprimir."))
        return self.env.ref(
            "todopintura_administration.action_custom_delivery_report"
        ).report_action(pickings)

    def action_print_paid_albaran_valued(self):
        self.ensure_one()
        self._ensure_conventional_paid_printable_order()
        pickings = self._get_conventional_reprint_pickings()
        if not pickings:
            raise UserError(_("Este pedido no tiene albaranes disponibles para imprimir."))
        return self.env.ref(
            "todopintura_extend_pos_conventional.action_custom_delivery_report_valued"
        ).report_action(pickings)

    def _get_conventional_paid_invoice_report(self):
        self.ensure_one()
        if self.is_a4_invoice:
            return (
                self.env.ref(
                    "todopintura_administration.action_report_invoice_custom",
                    raise_if_not_found=False,
                )
                or self.env.ref("account.account_invoices")
            )
        return (
            self.env.ref(
                "pos_conventional_receipt_custom.action_factura_simplificada_80mm_pdf",
                raise_if_not_found=False,
            )
            or self.env.ref("pos_conventional_receipt_custom.action_factura_simplificada_80mm")
        )

    def action_print_paid_invoice(self):
        self.ensure_one()
        self._ensure_conventional_paid_printable_order()
        if not self.account_move:
            raise UserError(_("Este pedido no tiene factura asociada para imprimir."))
        return self._get_conventional_paid_invoice_report().report_action(
            self.account_move
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

    @api.depends(
        "partner_id",
        "partner_id.commercial_partner_id",
        "amount_total",
        "amount_paid",
        "config_id",
        "config_id.picking_type_id",
        "config_id.picking_type_id.default_location_src_id",
    )
    def _compute_partner_credit_policy(self):
        for order in self:
            order.current_credit_location_name = False
            order.partner_credit_location_names = False
            order.partner_pickup_persons_display = False
            order.partner_pickup_persons_inline = False
            order.partner_requires_voucher = False
            order.partner_voucher_reference = False
            order.partner_current_total_due = 0.0
            order.partner_credit_limit_amount = 0.0
            order.partner_total_due_after_order = 0.0
            order.partner_credit_warning_message = False
            order.partner_credit_available = False
            order.partner_credit_cashier_warning = False
            if not order.partner_id:
                continue

            policy = order._get_conventional_credit_policy_data()
            order.current_credit_location_name = policy["current_location_name"]
            order.partner_credit_location_names = policy["allowed_location_names"]
            order.partner_pickup_persons_display = policy["pickup_people"]
            order.partner_pickup_persons_inline = order._format_pickup_people_inline(policy["pickup_people"])
            order.partner_requires_voucher = policy["requires_voucher"]
            order.partner_voucher_reference = policy["voucher_reference"]
            order.partner_current_total_due = policy["current_due"]
            order.partner_credit_limit_amount = policy["credit_limit"]
            order.partner_total_due_after_order = policy["total_after"]
            order.partner_credit_warning_message = policy["warning_message"]
            order.partner_credit_available = bool(
                policy["credit_sale_allowed"] and policy["location_allowed"]
            )
            if order.partner_credit_available:
                order.partner_credit_cashier_warning = _(
                    "ATENCIÓN: este cliente tiene crédito habilitado en esta caja. "
                    "Si la venta debe ir a cuenta, utilice el método 'Pago Cuenta de cliente' "
                    "para evitar cobrarla por efectivo o tarjeta por error."
                )

    def _format_pickup_people_inline(self, pickup_people):
        self.ensure_one()
        if not pickup_people:
            return False
        parts = [part.strip() for part in pickup_people.splitlines() if part.strip()]
        return ", ".join(parts) or pickup_people.strip()

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

    def _get_credit_source_location(self):
        self.ensure_one()
        return self.config_id.picking_type_id.default_location_src_id if self.config_id and self.config_id.picking_type_id else self.env["stock.location"]

    def has_draft_pay_later_payment(self):
        self.ensure_one()
        return bool(
            self.state == "draft"
            and self.payment_ids.filtered(
                lambda payment: payment.payment_method_id.type == "pay_later"
            )
        )

    def _get_partner_credit_policy_partner(self):
        self.ensure_one()
        return self.partner_id.commercial_partner_id

    def _get_credit_amount_to_check(self, amount=None):
        self.ensure_one()
        if amount is None:
            amount = max(self.amount_total - self.amount_paid, 0.0)
        return max(amount, 0.0)

    def _build_credit_warning_message(self, policy):
        self.ensure_one()
        lines = []
        if not policy["credit_sale_allowed"]:
            lines.append(policy["error_message"])
        elif not policy["location_allowed"]:
            lines.append(policy["location_error"])
        elif policy["needs_limit_override"]:
            lines.append(
                _(
                    "La deuda pendiente del cliente (%(current).2f) más esta venta (%(sale).2f) supera el límite de riesgo (%(limit).2f)."
                )
                % {
                    "current": policy["current_due"],
                    "sale": policy["order_amount"],
                    "limit": policy["credit_limit"],
                }
            )
        elif policy["limit_exceeded"]:
            lines.append(
                _("La venta supera el límite de riesgo, pero ya fue autorizada mediante override.")
            )


        return "\n".join(lines) or False

    def _get_conventional_credit_policy_data(self, amount=None, payment_method=None, allow_limit_override=False):
        self.ensure_one()

        partner = self._get_partner_credit_policy_partner()
        source_location = self._get_credit_source_location()
        currency = self.currency_id or self.company_id.currency_id
        order_amount = self._get_credit_amount_to_check(amount=amount)
        allowed_locations = partner._get_conventional_credit_locations() if partner else self.env["stock.location"]
        current_due = partner._get_conventional_total_due(self.config_id) if partner else 0.0
        credit_limit = partner._get_conventional_credit_limit(self.config_id) if partner else 0.0
        credit_limit_enabled = bool(
            partner
            and "use_partner_credit_limit" in partner._fields
            and partner.use_partner_credit_limit
            and credit_limit > 0
        )
        limit_exceeded = bool(
            credit_limit_enabled
            and float_compare(
                current_due + order_amount,
                credit_limit,
                precision_rounding=currency.rounding,
            )
            > 0
        )
        evaluate_as_credit_sale = payment_method.type == "pay_later" if payment_method else True
        credit_sale_allowed = bool(partner and partner.pos_credit_sale_enabled) if evaluate_as_credit_sale else True
        location_allowed = True
        location_error = False
        if evaluate_as_credit_sale and allowed_locations:
            location_allowed = bool(source_location and source_location in allowed_locations)
            if not source_location:
                location_error = _("La caja no tiene ubicación origen configurada.")
            elif not location_allowed:
                location_error = _(
                    "El cliente solo puede operarse a crédito en: %s. La caja actual usa: %s."
                ) % (", ".join(allowed_locations.mapped("display_name")), source_location.display_name)

        error_message = False
        if evaluate_as_credit_sale and not credit_sale_allowed:
            error_message = _("El cliente no está habilitado para ventas a crédito en POS convencional.")

        policy = {
            "order_amount": order_amount,
            "current_due": current_due,
            "credit_limit": credit_limit,
            "credit_limit_enabled": credit_limit_enabled,
            "limit_exceeded": limit_exceeded,
            "needs_limit_override": bool(evaluate_as_credit_sale and limit_exceeded and not allow_limit_override),
            "credit_sale_allowed": credit_sale_allowed,
            "location_allowed": location_allowed,
            "location_error": location_error,
            "error_message": error_message,
            "allowed_location_names": ", ".join(allowed_locations.mapped("display_name")) or False,
            "current_location_name": source_location.display_name if source_location else False,
            "pickup_people": partner._get_conventional_pickup_people_display() if partner else False,
            "requires_voucher": partner._uses_conventional_voucher() if partner else False,
            "voucher_reference": partner._get_conventional_voucher_reference() if partner else False,
            "total_after": current_due + order_amount,
        }
        policy["warning_message"] = self._build_credit_warning_message(policy)
        return policy

    def _open_credit_limit_override_wizard(self, payment_wizard, policy):
        self.ensure_one()
        action = self.env.ref(
            "todopintura_extend_pos_conventional.action_pos_conventional_credit_override_wizard"
        ).read()[0]
        action["context"] = {
            "default_order_id": self.id,
            "default_payment_wizard_id": payment_wizard.id,
            "default_current_due": policy["current_due"],
            "default_credit_limit": policy["credit_limit"],
            "default_payment_amount": policy["order_amount"],
            "default_total_after": policy["total_after"],
            "default_current_location_name": policy["current_location_name"],
            "default_allowed_location_names": policy["allowed_location_names"],
            "default_pickup_people": policy["pickup_people"],
            "default_requires_voucher": policy["requires_voucher"],
            "default_voucher_reference": policy["voucher_reference"],
            "default_warning_message": policy["warning_message"],
        }
        return action

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
        partner = self._get_partner_credit_policy_partner()
        if partner:
            if partner._uses_conventional_voucher():
                voucher_text = _("Cliente con vale requerido")
                if partner._get_conventional_voucher_reference():
                    voucher_text = _("%s: %s") % (
                        voucher_text,
                        partner._get_conventional_voucher_reference(),
                    )
                sale_note = "%s\n%s" % (sale_note, voucher_text)
            pickup_people = partner._get_conventional_pickup_people_display()
            if pickup_people:
                sale_note = "%s\n%s\n%s" % (
                    sale_note,
                    _("Autorizados de recogida:"),
                    pickup_people,
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

        reset_vals = {}
        if "to_invoice" in self._fields:
            reset_vals["to_invoice"] = False
        if "is_l10n_es_simplified_invoice" in self._fields:
            reset_vals["is_l10n_es_simplified_invoice"] = False
        if reset_vals:
            self.with_context(skip_completeness_check=True).write(reset_vals)

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

        if created_pickings and not self.env.context.get("skip_conventional_picking_print"):
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

        next_action = (
            self._get_conventional_post_validation_action_without_print()
            if self.env.context.get("skip_conventional_picking_print")
            else self._get_post_validation_action()
        )
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


    def _get_invoice_lines_values(self, line_values, pos_line, move_type):
        res = super()._get_invoice_lines_values(line_values, pos_line, move_type)
        default_warehouse = self.origin_warehouse_id or self.config_id.warehouse_id
        if pos_line.pickup_warehouse_id and pos_line.pickup_warehouse_id != default_warehouse:
            res["pickup_warehouse_id"] = pos_line.pickup_warehouse_id.id
        return res


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    pickup_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Tienda de recogida",
    )
    stock_status = fields.Selection(
        selection=[
            ('available', 'Disponible'),
            ('partial', 'Parcialmente'),
            ('out', 'Sin Stock'),
        ],
        string="Estado Stock",
        compute="_compute_stock_status",
        store=True,
    )
    is_available_in_warehouse = fields.Boolean(
        string="Disponible en tienda (Legacy)",
        help="Campo dummy para evitar errores de vista durante la transición",
    )

    # Campos necesarios para que el widget 'qty_at_date_widget' funcione (bocadillo de comic)
    display_qty_widget = fields.Boolean(compute="_compute_qty_at_date_data")
    free_qty_today = fields.Float(compute="_compute_qty_at_date_data")
    forecast_expected_date = fields.Datetime(compute="_compute_qty_at_date_data")
    is_mto = fields.Boolean(compute="_compute_qty_at_date_data")
    move_ids = fields.One2many('stock.move', compute="_compute_qty_at_date_data")
    qty_available_today = fields.Float(compute="_compute_qty_at_date_data")
    qty_to_deliver = fields.Float(compute="_compute_qty_at_date_data")
    scheduled_date = fields.Datetime(compute="_compute_qty_at_date_data")
    virtual_available_at_date = fields.Float(compute="_compute_qty_at_date_data")
    warehouse_id = fields.Many2one('stock.warehouse', compute="_compute_qty_at_date_data")
    stock_at_locations_json = fields.Text(compute="_compute_stock_at_locations_json")
    state = fields.Selection(related="order_id.state")

    def _compute_stock_at_locations_json(self):
        for line in self:
            if not line.product_id:
                line.stock_at_locations_json = "[]"
                continue
            quants = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0)
            ])
            data = []
            # Agrupar por almacén para que sea más legible
            wh_stocks = {}
            for q in quants:
                wh_name = q.warehouse_id.name or q.location_id.display_name
                wh_stocks[wh_name] = wh_stocks.get(wh_name, 0.0) + q.available_quantity

            for name, qty in wh_stocks.items():
                data.append({'location': name, 'qty': qty})
            line.stock_at_locations_json = json.dumps(data)

    @api.depends('product_id', 'qty', 'pickup_warehouse_id')
    def _compute_qty_at_date_data(self):
        for line in self:
            warehouse = line.pickup_warehouse_id or line.order_id.config_id.warehouse_id
            product = line.product_id

            # En Odoo 19 'consu' suele ser el tipo para productos con stock (Goods)
            is_storable = product and product.type == 'consu'

            line.display_qty_widget = is_storable
            line.warehouse_id = warehouse.id if warehouse else False
            line.qty_to_deliver = line.qty
            line.scheduled_date = line.order_id.date_order or fields.Datetime.now()

            if is_storable and warehouse:
                res = product.with_context(warehouse_id=warehouse.id)._compute_quantities_dict(None, None, None)
                qty_data = res.get(product.id, {})
                line.free_qty_today = qty_data.get('free_qty', 0.0)
                line.virtual_available_at_date = qty_data.get('virtual_available', 0.0)
                line.qty_available_today = qty_data.get('qty_available', 0.0)
            else:
                line.free_qty_today = 0.0
                line.virtual_available_at_date = 0.0
                line.qty_available_today = 0.0

            line.forecast_expected_date = False
            line.is_mto = False
            line.move_ids = self.env['stock.move']

    @api.onchange('product_id', 'qty', 'pickup_warehouse_id')
    def _onchange_refresh_stock_widget_data(self):
        for line in self:
            if line.order_id and not line.pickup_warehouse_id:
                line.pickup_warehouse_id = line.order_id.config_id.warehouse_id
        self._compute_qty_at_date_data()
        self._compute_stock_at_locations_json()

    @api.depends('product_id', 'qty', 'pickup_warehouse_id', 'order_id.config_id.warehouse_id')
    def _compute_stock_status(self):
        for line in self:
            if not line.product_id or line.product_id.type != 'consu':
                line.stock_status = 'available'
                continue

            # 1. Stock en la tienda seleccionada (o tienda origen)
            warehouse = line.pickup_warehouse_id or line.order_id.origin_warehouse_id
            if not warehouse:
                line.stock_status = 'out'
                continue

            res = line.product_id.with_context(warehouse_id=warehouse.id)._compute_quantities_dict(None, None, None)
            available_qty = res.get(line.product_id.id, {}).get('free_qty', 0.0)

            if available_qty >= line.qty:
                line.stock_status = 'available'
            else:
                # 2. Si no hay en esta tienda, ver si hay en la suma de todas las tiendas (internal locations)
                all_res = line.product_id._compute_quantities_dict(None, None, None)
                total_available = all_res.get(line.product_id.id, {}).get('free_qty', 0.0)
                if total_available >= line.qty:
                    line.stock_status = 'partial'
                else:
                    line.stock_status = 'out'

    def action_open_stock_forecast(self):
        self.ensure_one()
        # Mantenemos el modal para ver detalles por ubicación si el usuario pulsa en el semáforo
        action = {
            'name': _('Disponibilidad de: %s') % self.product_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'list',
            'domain': [
                ('product_id', '=', self.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('quantity', '>', 0)
            ],
            'context': {
                'search_default_internal_p_loc': True,
                'dialog_size': 'large',
            },
            'target': 'new',
        }
        view_id = self.env.ref('todopintura_extend_pos_conventional.view_stock_quant_pos_modal_tree').id
        action['views'] = [(view_id, 'list')]
        return action

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


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pickup_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Tienda de recogida",
        help="Tienda desde la que se servirá esta línea de factura creada desde POS.",
    )



