# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models

COST_GROUP = "todopintura_user_groups.group_cost_viewer"


class PosOrder(models.Model):
    _inherit = "pos.order"

    margin = fields.Monetary(groups=COST_GROUP)
    margin_percent = fields.Float(groups=COST_GROUP)


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    margin = fields.Monetary(groups=COST_GROUP)
    margin_percent = fields.Float(groups=COST_GROUP)


class PosReport(models.Model):
    """Pivot/graph measures come from the model fields, so the margin of the
    POS analysis report is restricted at field level (read-only model)."""

    _inherit = "report.pos.order"

    margin = fields.Float(groups=COST_GROUP)
