# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pos_deposit_sale_enabled = fields.Boolean(
        string="Permitir venta en depósito en POS",
        help=(
            "Permite reservar ventas en depósito para las tiendas indicadas abajo. "
            "Es independiente de la venta a crédito: un cliente puede tener ambas."
        ),
    )
    pos_conventional_sale_mode = fields.Selection(
        selection=[
            ("none", "Vacío"),
            ("credit", "Crédito"),
            ("deposit", "Depósito"),
            ("both", "Crédito y depósito"),
        ],
        string="Modo de venta POS convencional",
        default="none",
        help=(
            "Resumen de 'Permitir venta a crédito en POS' y 'Permitir venta en "
            "depósito en POS', que son independientes. Se mantiene sincronizado por "
            "compatibilidad."
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
    def _mode_from_flags(self, credit, deposit):
        if credit and deposit:
            return "both"
        if credit:
            return "credit"
        if deposit:
            return "deposit"
        return "none"

    @api.model
    def _synchronize_pos_conventional_mode_vals(self, vals):
        """Sincroniza el selector resumen con los dos booleanos independientes.

        Si se escribe el selector, manda sobre los booleanos. Si solo se escriben
        booleanos, el selector se recalcula (con el valor actual del otro flag).
        """
        if "pos_conventional_sale_mode" in vals:
            mode = vals["pos_conventional_sale_mode"] or "none"
            vals["pos_conventional_sale_mode"] = mode
            vals["pos_credit_sale_enabled"] = mode in ("credit", "both")
            vals["pos_deposit_sale_enabled"] = mode in ("deposit", "both")
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            vals = self._synchronize_pos_conventional_mode_vals(dict(vals))
            if "pos_conventional_sale_mode" not in vals and (
                "pos_credit_sale_enabled" in vals or "pos_deposit_sale_enabled" in vals
            ):
                vals["pos_conventional_sale_mode"] = self._mode_from_flags(
                    vals.get("pos_credit_sale_enabled"),
                    vals.get("pos_deposit_sale_enabled"),
                )
            new_vals_list.append(vals)
        return super().create(new_vals_list)

    def write(self, vals):
        vals = self._synchronize_pos_conventional_mode_vals(dict(vals))
        flags_only = "pos_conventional_sale_mode" not in vals and (
            "pos_credit_sale_enabled" in vals or "pos_deposit_sale_enabled" in vals
        )
        res = super().write(vals)
        if flags_only:
            for partner in self:
                mode = self._mode_from_flags(
                    partner.pos_credit_sale_enabled, partner.pos_deposit_sale_enabled
                )
                if partner.pos_conventional_sale_mode != mode:
                    super(ResPartner, partner).write({"pos_conventional_sale_mode": mode})
        return res

    def _is_pos_credit_enabled(self):
        self.ensure_one()
        return bool(self.pos_credit_sale_enabled)

    def _is_pos_deposit_enabled(self):
        self.ensure_one()
        return bool(self.pos_deposit_sale_enabled)

    def _get_pos_conventional_sale_mode(self):
        self.ensure_one()
        return self._mode_from_flags(
            self.pos_credit_sale_enabled, self.pos_deposit_sale_enabled
        )

    def _get_conventional_credit_locations(self):
        """La venta a crédito no se restringe por tienda (las tiendas son solo del depósito)."""
        self.ensure_one()
        return self.env["stock.location"]

    def _get_pos_deposit_locations(self):
        self.ensure_one()
        if not self.pos_deposit_sale_enabled:
            return self.env["stock.location"]
        return self.pos_credit_location_ids
