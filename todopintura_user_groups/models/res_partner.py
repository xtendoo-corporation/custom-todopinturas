# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    route_id = fields.Many2one(
        "todopintura.route", string="Zona de ruta", index=True, ondelete="set null"
    )
    visit_day_ids = fields.Many2many(
        "todopintura.weekday",
        "res_partner_visit_day_rel",
        "partner_id",
        "weekday_id",
        string="Días de visita",
    )
    route_user_id = fields.Many2one(
        related="route_id.user_id",
        string="Comercial de la ruta",
        store=True,
        index=True,
    )
