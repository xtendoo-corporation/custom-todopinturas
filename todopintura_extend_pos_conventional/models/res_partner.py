# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartnerPickupPerson(models.Model):
    _name = "res.partner.pickup.person"
    _description = "Persona autorizada para recogida"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="partner_id.company_id",
        store=True,
        readonly=True,
    )
    name = fields.Char(string="Nombre", required=True)
    vat = fields.Char(string="DNI/NIF")
    phone = fields.Char(string="Teléfono")
    notes = fields.Char(string="Observaciones")


class ResPartner(models.Model):
    _inherit = "res.partner"

    pos_requires_voucher = fields.Boolean(string="Necesita vale")
    pos_voucher_reference = fields.Char(string="Código / documento del vale")
    pos_credit_sale_enabled = fields.Boolean(string="Permitir venta a crédito en POS")
    pos_credit_location_ids = fields.Many2many(
        comodel_name="stock.location",
        relation="res_partner_pos_credit_location_rel",
        column1="partner_id",
        column2="location_id",
        string="Ubicaciones permitidas para cobro/crédito",
        domain="[('usage', '=', 'internal')]",
        help="Si se indican ubicaciones, solo se permitirá vender/cobrar a crédito desde cajas cuya ubicación origen pertenezca a esta lista.",
    )
    pos_pickup_person_ids = fields.One2many(
        comodel_name="res.partner.pickup.person",
        inverse_name="partner_id",
        string="Autorizados de recogida",
    )
    pos_credit_location_names = fields.Char(
        string="Ubicaciones permitidas",
        compute="_compute_pos_credit_metadata",
    )
    pos_pickup_persons_summary = fields.Text(
        string="Resumen autorizados de recogida",
        compute="_compute_pos_credit_metadata",
    )
    pos_has_pickup_persons = fields.Boolean(
        string="Tiene autorizados de recogida",
        compute="_compute_pos_credit_metadata",
    )

    @api.model
    def _todopintura_company_partner_domain(self, domain=None):
        domain = list(domain or [])
        if (
            self.env.context.get("todopintura_company_partner_only")
            or self.env.context.get("res_partner_search_mode") == "customer"
        ):
            domain.extend([
                ("is_company", "=", True),
                ("parent_id", "=", False),
            ])
        return domain

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        domain = self._todopintura_company_partner_domain(domain)
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

    @api.model
    def web_name_search(self, name, specification, domain=None, operator="ilike", limit=100):
        domain = self._todopintura_company_partner_domain(domain)
        return super().web_name_search(
            name,
            specification,
            domain=domain,
            operator=operator,
            limit=limit,
        )

    @api.depends(
        "pos_credit_location_ids",
        "pos_credit_location_ids.display_name",
        "pos_pickup_person_ids",
        "pos_pickup_person_ids.active",
        "pos_pickup_person_ids.name",
        "pos_pickup_person_ids.vat",
        "pos_pickup_person_ids.phone",
    )
    def _compute_pos_credit_metadata(self):
        for partner in self:
            locations = partner._get_conventional_credit_locations()
            partner.pos_credit_location_names = ", ".join(locations.mapped("display_name")) or False

            structured_people = []
            for person in partner.pos_pickup_person_ids.filtered("active"):
                label = person.name
                if person.vat:
                    label = "%s (%s)" % (label, person.vat)
                structured_people.append(label)

            legacy_info = False
            if not structured_people and "assigned_persons_info" in partner._fields:
                legacy_info = partner.assigned_persons_info or False

            partner.pos_pickup_persons_summary = "\n".join(structured_people) or legacy_info or False
            partner.pos_has_pickup_persons = bool(partner.pos_pickup_persons_summary)

    def _get_conventional_credit_locations(self):
        self.ensure_one()
        locations = self.pos_credit_location_ids
        if not locations and "credit_location_id" in self._fields and self.credit_location_id:
            locations |= self.credit_location_id
        return locations

    def _uses_conventional_voucher(self):
        self.ensure_one()
        return bool(self.pos_requires_voucher or ("voucher" in self._fields and self.voucher))

    def _get_conventional_voucher_reference(self):
        self.ensure_one()
        return self.pos_voucher_reference or False

    def _get_conventional_pickup_people_display(self):
        self.ensure_one()
        if self.pos_pickup_persons_summary:
            return self.pos_pickup_persons_summary
        if "assigned_persons_info" in self._fields:
            return self.assigned_persons_info or False
        return False

    def _get_conventional_total_due(self, config):
        self.ensure_one()
        partner = self.commercial_partner_id
        total_due = 0.0
        if hasattr(partner, "get_total_due") and config:
            payload = partner.get_total_due(config.id)
            total_due = payload.get("res.partner", [{}])[0].get("total_due", 0.0)
        elif "total_due" in partner._fields:
            total_due = partner.sudo().total_due
            if config and config.currency_id != self.env.company.currency_id:
                total_due = self.env.company.currency_id._convert(
                    total_due,
                    config.currency_id,
                    self.env.company,
                    fields.Date.today(),
                )
        return total_due

    def _get_conventional_credit_limit(self, config):
        self.ensure_one()
        partner = self.commercial_partner_id
        if "credit_limit" not in partner._fields:
            return 0.0
        credit_limit = partner.sudo().credit_limit or 0.0
        if config and config.currency_id != self.env.company.currency_id:
            credit_limit = self.env.company.currency_id._convert(
                credit_limit,
                config.currency_id,
                self.env.company,
                fields.Date.today(),
            )
        return credit_limit
