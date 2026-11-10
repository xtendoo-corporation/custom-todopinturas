# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    todopintura_is_commercial = fields.Boolean(compute="_compute_todopintura_is_commercial")

    @api.depends_context("uid")
    def _compute_todopintura_is_commercial(self):
        blocked = self._todopintura_commercial_blocked()
        for order in self:
            order.todopintura_is_commercial = blocked

    @api.model
    def _todopintura_commercial_blocked(self):
        user = self.env.user
        return not self.env.su and user.is_commercial and not user.has_group("base.group_system")

    def action_confirm(self):
        if self._todopintura_commercial_blocked():
            raise UserError(
                self.env._(
                    "Los comerciales no pueden confirmar presupuestos: "
                    "solo enviarlos al cliente."
                )
            )
        return super().action_confirm()

    def action_open_purchase_history(self):
        """Customer purchase history built on the existing order lines (no copy)."""
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Historial de compras de %s", partner.display_name),
            "res_model": "sale.order.line",
            "views": [
                (
                    self.env.ref(
                        "todopintura_user_groups.sale_order_line_history_list"
                    ).id,
                    "list",
                ),
                (
                    self.env.ref(
                        "todopintura_user_groups.sale_order_line_history_pivot"
                    ).id,
                    "pivot",
                ),
            ],
            "domain": [
                ("order_partner_id", "child_of", partner.id),
                ("order_id", "!=", self.id),
                ("display_type", "=", False),
                "|",
                ("qty_invoiced", ">", 0),
                ("qty_delivered", ">", 0),
            ],
            "context": {"group_by": ["product_id"], "create": False},
        }
