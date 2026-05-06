# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pos_conventional_sale_mode = fields.Selection(
        selection=[
            ("none", "Vacío"),
            ("credit", "Crédito"),
            ("deposit", "Depósito"),
        ],
        string="Modo de venta POS convencional",
        default="none",
        help=(
            "Crédito: permite venta a crédito en cualquier tienda. "
            "Depósito: reserva las ventas en depósito para las tiendas indicadas abajo."
        ),
    )
    pos_credit_location_ids = fields.Many2many(
        comodel_name="stock.location",
        relation="res_partner_pos_credit_location_rel",
        column1="partner_id",
        column2="location_id",
        string="Tiendas permitidas para depósito",
        domain="[('usage', '=', 'internal')]",
        help=(
            "Si el modo es 'Depósito', solo se permitirán ventas en depósito desde "
            "cajas cuya ubicación origen pertenezca a esta lista. Si se deja vacío, "
            "no se restringe por tienda."
        ),
    )

    @api.model
    def _synchronize_pos_conventional_mode_vals(self, vals):
        if "pos_conventional_sale_mode" in vals:
            mode = vals["pos_conventional_sale_mode"] or "none"
            vals["pos_conventional_sale_mode"] = mode
            vals["pos_credit_sale_enabled"] = mode == "credit"
        elif "pos_credit_sale_enabled" in vals:
            vals["pos_conventional_sale_mode"] = (
                "credit" if vals["pos_credit_sale_enabled"] else "none"
            )
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [
            self._synchronize_pos_conventional_mode_vals(dict(vals))
            for vals in vals_list
        ]
        return super().create(vals_list)

    def write(self, vals):
        vals = self._synchronize_pos_conventional_mode_vals(dict(vals))
        return super().write(vals)

    def _get_pos_conventional_sale_mode(self):
        self.ensure_one()
        if self.pos_conventional_sale_mode in {"none", "credit", "deposit"}:
            return self.pos_conventional_sale_mode
        return "credit" if self.pos_credit_sale_enabled else "none"

    def _get_conventional_credit_locations(self):
        self.ensure_one()
        if self._get_pos_conventional_sale_mode() != "deposit":
            return self.env["stock.location"]
        return super()._get_conventional_credit_locations()


