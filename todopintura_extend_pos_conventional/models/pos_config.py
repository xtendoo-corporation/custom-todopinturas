# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    conventional_source_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Ubicación de la caja POS conventional",
        related="picking_type_id.default_location_src_id",
        readonly=True,
    )

    def _is_conventional_pos_config(self):
        self.ensure_one()
        return bool(getattr(self, "pos_non_touch", False))

    def _ensure_conventional_source_location(self):
        for config in self:
            if not config._is_conventional_pos_config():
                continue
            if not config.picking_type_id:
                raise ValidationError(
                    _(
                        "La caja POS Conventional '%(config)s' debe tener un tipo de operación configurado."
                    )
                    % {"config": config.display_name}
                )
            if not config.conventional_source_location_id:
                raise ValidationError(
                    _(
                        "La caja POS Conventional '%(config)s' debe estar vinculada a una ubicación. "
                        "Configure una ubicación origen en el tipo de operación '%(operation)s'."
                    )
                    % {
                        "config": config.display_name,
                        "operation": config.picking_type_id.display_name,
                    }
                )

    @api.constrains("pos_non_touch", "picking_type_id")
    def _check_conventional_source_location(self):
        self._ensure_conventional_source_location()

    def open_ui(self):
        self._ensure_conventional_source_location()
        return super().open_ui()

