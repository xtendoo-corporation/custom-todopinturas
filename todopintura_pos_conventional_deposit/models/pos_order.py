# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class PosOrder(models.Model):
    _inherit = "pos.order"

    state = fields.Selection(
        selection_add=[
            ("deposit", "En depósito"),
        ],
        ondelete={"deposit": "set default"},
    )



    partner_deposit_enabled = fields.Boolean(
        string="Cliente configurado para depósito",
        compute="_compute_partner_deposit_policy",
    )
    partner_deposit_available = fields.Boolean(
        string="Depósito disponible en esta tienda",
        compute="_compute_partner_deposit_policy",
    )
    partner_deposit_location_names = fields.Char(
        string="Tiendas permitidas para depósito",
        compute="_compute_partner_deposit_policy",
    )
    partner_deposit_warning_message = fields.Text(
        string="Aviso de depósito",
        compute="_compute_partner_deposit_policy",
    )
    show_deposit_button = fields.Boolean(
        string="Mostrar botón depósito",
        compute="_compute_partner_deposit_policy",
    )

    def _get_conventional_credit_policy_data(
        self, amount=None, payment_method=None, allow_limit_override=False
    ):
        policy = super()._get_conventional_credit_policy_data(
            amount=amount,
            payment_method=payment_method,
            allow_limit_override=allow_limit_override,
        )
        partner = self._get_partner_credit_policy_partner()
        payment_method = self._normalize_conventional_payment_method(payment_method)
        evaluate_as_credit_sale = payment_method.type == "pay_later" if payment_method else True
        if not (partner and evaluate_as_credit_sale):
            return policy

        if partner._get_pos_conventional_sale_mode() == "deposit":
            policy["credit_sale_allowed"] = False
            policy["needs_limit_override"] = False
            policy["error_message"] = _(
                "El cliente está configurado para ventas en depósito y no para ventas a crédito en POS convencional."
            )
            policy["warning_message"] = self._build_credit_warning_message(policy)
        return policy

    def _get_conventional_deposit_policy_data(self):
        self.ensure_one()

        partner = self._get_partner_credit_policy_partner()
        source_location = self._get_credit_source_location()
        deposit_enabled = bool(
            partner and partner._get_pos_conventional_sale_mode() == "deposit"
        )
        allowed_locations = (
            partner._get_conventional_credit_locations()
            if deposit_enabled and partner
            else self.env["stock.location"]
        )
        location_allowed = True
        warning_message = False
        if deposit_enabled and allowed_locations:
            location_allowed = bool(source_location and source_location in allowed_locations)
            if not source_location:
                warning_message = _(
                    "La caja no tiene ubicación origen configurada para realizar depósitos."
                )
            elif not location_allowed:
                warning_message = _(
                    "El cliente solo puede operarse en depósito en: %s. La caja actual usa: %s."
                ) % (
                    ", ".join(allowed_locations.mapped("display_name")),
                    source_location.display_name,
                )

        return {
            "deposit_enabled": deposit_enabled,
            "deposit_available": bool(deposit_enabled and location_allowed),
            "location_allowed": location_allowed,
            "warning_message": warning_message,
            "allowed_location_names": ", ".join(allowed_locations.mapped("display_name"))
            or False,
        }

    @api.depends(
        "partner_id",
        "partner_id.commercial_partner_id",
        "partner_id.commercial_partner_id.pos_conventional_sale_mode",
        "partner_id.commercial_partner_id.pos_credit_location_ids",
        "partner_id.commercial_partner_id.pos_credit_location_ids.display_name",
        "config_id",
        "config_id.picking_type_id",
        "config_id.picking_type_id.default_location_src_id",
        "state",
        "payment_ids",
        "is_linked_to_sale",
    )
    def _compute_partner_deposit_policy(self):
        for order in self:
            order.partner_deposit_enabled = False
            order.partner_deposit_available = False
            order.partner_deposit_location_names = False
            order.partner_deposit_warning_message = False
            order.show_deposit_button = False
            if not order.partner_id:
                continue

            policy = order._get_conventional_deposit_policy_data()
            order.partner_deposit_enabled = policy["deposit_enabled"]
            order.partner_deposit_available = policy["deposit_available"]
            order.partner_deposit_location_names = policy["allowed_location_names"]
            order.partner_deposit_warning_message = policy["warning_message"]
            order.show_deposit_button = bool(
                order.state == "draft"
                and policy["deposit_available"]
                and not order.payment_ids
                and not order.is_linked_to_sale
            )

    def _get_or_create_conventional_deposit_location(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        location = self.env["stock.location"].search(
            [
                ("name", "=", "Depósito"),
                ("usage", "=", "transit"),
                ("company_id", "in", [False, company.id]),
            ],
            limit=1,
            order="company_id desc, id asc",
        )
        if location:
            return location

        return self.env["stock.location"].sudo().create(
            {
                "name": "Depósito",
                "usage": "transit",
                "company_id": company.id,
                "active": True,
            }
        )

    def _get_conventional_deposit_lines(self):
        self.ensure_one()
        return self.lines.filtered(
            lambda line: line.product_id.type == "consu"
            and not line.product_id.uom_id.is_zero(line.qty)
        )

    def action_pay_deposit(self):
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
                _("Solo se pueden enviar a depósito pedidos en estado borrador.")
            )
        if not self.lines:
            raise UserError(
                _("No se puede crear un depósito de un pedido sin líneas de producto.")
            )
        if not self.partner_id:
            raise UserError(
                _("Debe seleccionar un cliente para crear un pedido en depósito.")
            )
        if self.payment_ids:
            raise UserError(
                _("No puede crear un depósito sobre un pedido que ya tiene pagos registrados.")
            )

        partner = self._get_partner_credit_policy_partner()
        if not partner or partner._get_pos_conventional_sale_mode() != "deposit":
            raise UserError(
                _("El cliente seleccionado no está configurado para ventas en depósito.")
            )

        deposit_policy = self._get_conventional_deposit_policy_data()
        if not deposit_policy["deposit_available"]:
            raise UserError(
                deposit_policy["warning_message"]
                or _(
                    "El cliente no tiene habilitadas ventas en depósito en esta tienda."
                )
            )

        deposit_lines = self._get_conventional_deposit_lines()
        if not deposit_lines:
            raise UserError(
                _(
                    "El pedido debe contener al menos un producto almacenable para generar el depósito."
                )
            )

        if self.name == "/":
            sequence = self.env["ir.sequence"].sudo().search([("code", "=", "pos.order.deposit")], limit=1)
            if not sequence:
                sequence = self.env["ir.sequence"].sudo().create({
                    "name": "POS Conventional Deposit Sequence",
                    "code": "pos.order.deposit",
                    "prefix": "DEPO/",
                    "padding": 4,
                    "number_next": 1,
                    "number_increment": 1,
                })
            self.write({"name": sequence._next()})

        deposit_location = self._get_or_create_conventional_deposit_location()
        created_pickings = self.env["stock.picking"]
        for group in self._group_lines_by_pickup_warehouse(lines=deposit_lines):
            picking_type = self._get_fulfillment_picking_type(group["warehouse"])
            pickings = self.env["stock.picking"]._create_picking_from_pos_order_lines(
                deposit_location.id,
                group["lines"],
                picking_type,
                self.partner_id,
            )
            if pickings:
                pickings.write(
                    {
                        "pos_session_id": self.session_id.id,
                        "pos_order_id": self.id,
                        "origin": self.name,
                    }
                )
                created_pickings |= pickings

        if not created_pickings:
            raise UserError(
                _("No se pudo generar el picking de depósito para este pedido.")
            )

        self.write({"state": "deposit"})
        action = self.env["ir.actions.act_window"]._for_xml_id("point_of_sale.action_pos_pos_form")
        action.update({
            "views": [[False, "form"]],
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
            "context": {
                **self.env.context,
                "default_session_id": self.session_id.id,
            },
        })
        return action

    @api.model
    def _get_conventional_deposit_session_from_context(self):
        session_id = self.env.context.get("default_session_id") or self.env.context.get("session_id")
        if (
            not session_id
            and self.env.context.get("active_model") == "pos.order"
            and self.env.context.get("active_id")
        ):
            active_order = self.env["pos.order"].browse(self.env.context["active_id"]).exists()
            session_id = active_order.session_id.id if active_order else False
        return self.env["pos.session"].browse(int(session_id)).exists() if session_id else self.env["pos.session"]

    @api.model
    def action_open_deposit_payment_wizard(self):
        session = self._get_conventional_deposit_session_from_context()
        if not session:
            raise UserError(
                _(
                    "No se ha podido determinar la caja/sesión activa para pagar depósitos."
                )
            )

        view = self.env.ref(
            "todopintura_pos_conventional_deposit.view_pos_deposit_payment_wizard_form"
        )
        wizard = self.env["pos.deposit.payment.wizard"].create(
            {
                "session_id": session.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Cobrar depósitos"),
            "res_model": "pos.deposit.payment.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "view_id": view.id,
            "views": [(view.id, "form")],
            "target": "new",
            "context": {
                **self.env.context,
                "default_session_id": session.id,
                "dialog_size": "medium",
            },
        }

    def _create_conventional_deposit_invoice(self, invoice_partner=None):
        orders = self.exists()
        if not orders:
            raise UserError(_("No hay pedidos en depósito para facturar."))

        companies = orders.mapped("company_id")
        configs = orders.mapped("config_id")
        currencies = orders.mapped("currency_id")
        fiscal_positions = orders.mapped("fiscal_position_id")
        partners = orders.mapped("partner_id")
        commercial_partners = partners.mapped("commercial_partner_id")

        if len(companies) > 1 or len(configs) > 1 or len(currencies) > 1:
            raise UserError(
                _(
                    "Los pedidos seleccionados deben pertenecer a la misma compañía, caja y moneda."
                )
            )
        if len(fiscal_positions) > 1:
            raise UserError(
                _(
                    "Los pedidos seleccionados deben usar la misma posición fiscal para generar una sola factura."
                )
            )
        if len(commercial_partners) > 1:
            raise UserError(
                _(
                    "Los pedidos seleccionados deben pertenecer al mismo cliente comercial."
                )
            )
        if any(order.state != "deposit" for order in orders):
            raise UserError(
                _("Solo se pueden facturar pedidos que estén actualmente en depósito.")
            )
        if any(order.account_move for order in orders):
            raise UserError(
                _("Alguno de los pedidos seleccionados ya tiene una factura asociada.")
            )

        reference_order = orders[:1]
        company = companies[:1]
        config = configs[:1]
        invoice_partner = (invoice_partner or partners[:1]).commercial_partner_id
        invoice_vals = reference_order._prepare_invoice_vals()

        if len(orders) > 1:
            invoice_line_ids = list(invoice_vals.get("invoice_line_ids", []))
            for order in (orders - reference_order):
                invoice_line_ids.extend(order._prepare_invoice_lines(invoice_vals["move_type"]))
            invoice_vals.update({
                "invoice_line_ids": invoice_line_ids,
                "invoice_origin": ", ".join(ref or "" for ref in orders.mapped("pos_reference")),
                "pos_order_ids": orders.ids,
            })

        deposit_invoice_journal = orders._get_conventional_deposit_invoice_journal(config=config)
        invoice_vals.update(
            {
                "partner_id": invoice_partner.address_get(["invoice"])["invoice"],
                "partner_shipping_id": invoice_partner.address_get(["delivery"])["delivery"],
                "partner_bank_id": orders.with_context(active_test=False)
                .with_company(company)
                ._get_partner_bank_id(),
                "invoice_user_id": self.env.user.id,
                "ref": ", ".join(orders.mapped("name")) if len(orders) == 1 else False,
                "journal_id": deposit_invoice_journal.id,
            }
        )

        invoice = orders._create_invoice(invoice_vals)
        invoice.sudo().with_company(company).with_context(
            **reference_order._get_invoice_post_context()
        )._post()

        for order in orders:
            write_vals = {
                "account_move": invoice.id,
                "state": "done",
                "to_invoice": False,
            }
            if "is_l10n_es_simplified_invoice" in order._fields:
                write_vals["is_l10n_es_simplified_invoice"] = True
            order.with_context(skip_completeness_check=True).write(write_vals)
        return invoice

    def _get_conventional_deposit_invoice_journal(self, config=None):
        orders = self.exists()
        reference_order = orders[:1]
        config = config or reference_order.config_id
        if not config:
            raise UserError(_("No se ha podido determinar la caja para elegir el diario de factura."))

        simplified_journal = getattr(config, "l10n_es_simplified_invoice_journal_id", self.env["account.journal"])
        if config.journal_id and config.journal_id.type == "sale":
            return config.journal_id

        if simplified_journal and simplified_journal != config.invoice_journal_id:
            return simplified_journal

        raise UserError(
            _(
                "La caja '%(config)s' no tiene configurado un diario de factura de TPV válido para depósitos. "
                "Configure el diario de factura simplificada/TPV en la caja y vuelva a intentarlo."
            )
            % {"config": config.display_name}
        )

