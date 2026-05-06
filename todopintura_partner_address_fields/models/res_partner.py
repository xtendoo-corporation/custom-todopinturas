# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ResPartner(models.Model):
    _inherit = "res.partner"

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "country_id" in fields_list and "country_id" not in res:
            spain = self.env.ref("base.es", raise_if_not_found=False)
            if spain:
                res["country_id"] = spain.id
        return res

    @api.constrains("vat", "company_id")
    def _check_vat_unique_by_company_scope(self):
        partner_model = self.sudo().with_context(active_test=False)
        for partner in self:
            vat = (partner.vat or "").strip()
            if not vat:
                continue

            if partner.company_id:
                domain = [
                    ("id", "!=", partner.id),
                    ("vat", "=", vat),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", partner.company_id.id),
                ]
            else:
                domain = [
                    ("id", "!=", partner.id),
                    ("vat", "=", vat),
                ]

            duplicate = partner_model.search(domain, limit=1)
            if duplicate:
                if partner.company_id and not duplicate.company_id:
                    raise ValidationError(
                        _(
                            "No se puede guardar el contacto con DNI/NIF '%(vat)s'. "
                            "Ya existe un contacto global con ese mismo DNI/NIF: %(partner)s."
                        )
                        % {"vat": vat, "partner": duplicate.display_name}
                    )
                if not partner.company_id:
                    raise ValidationError(
                        _(
                            "No se puede guardar el contacto global con DNI/NIF '%(vat)s'. "
                            "Ese DNI/NIF ya existe en el contacto: %(partner)s."
                        )
                        % {"vat": vat, "partner": duplicate.display_name}
                    )
                raise ValidationError(
                    _(
                        "No se puede guardar el contacto con DNI/NIF '%(vat)s' para la compañía "
                        "'%(company)s'. Ya existe otro contacto en el mismo alcance: %(partner)s."
                    )
                    % {
                        "vat": vat,
                        "company": partner.company_id.display_name,
                        "partner": duplicate.display_name,
                    }
                )
