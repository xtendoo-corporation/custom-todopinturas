# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class TodopinturaWeekday(models.Model):
    _name = "todopintura.weekday"
    _description = "Día de visita"
    _order = "sequence"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(required=True)

    _sequence_uniq = models.Constraint(
        "UNIQUE(sequence)", "Cada día de la semana solo puede existir una vez."
    )


class TodopinturaRoute(models.Model):
    _name = "todopintura.route"
    _description = "Ruta de comercial"
    _order = "user_id, name"

    name = fields.Char(string="Zona", required=True)
    user_id = fields.Many2one(
        "res.users",
        string="Comercial responsable",
        required=True,
        domain=[("share", "=", False)],
        index=True,
    )
    active = fields.Boolean(default=True)
    partner_ids = fields.One2many("res.partner", "route_id", string="Clientes")
    partner_count = fields.Integer(compute="_compute_partner_count")

    _name_user_uniq = models.Constraint(
        "UNIQUE(name, user_id)", "Ya existe esa zona para el comercial."
    )

    def _compute_partner_count(self):
        counts = dict(
            self.env["res.partner"]._read_group(
                [("route_id", "in", self.ids)], ["route_id"], ["__count"]
            )
        )
        for route in self:
            route.partner_count = counts.get(route, 0)
