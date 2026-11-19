# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class PosSessionClosingWizard(models.TransientModel):
    """Cierre de caja desde el asistente de backend: avisa de los pedidos en borrador
    y permite borrarlos y cerrar (en el popup del TPV lo hace el parche de JS)."""

    _inherit = "pos.session.closing.wizard"

    draft_order_count = fields.Integer(compute="_compute_draft_orders")
    draft_order_names = fields.Char(compute="_compute_draft_orders")

    @api.depends("session_id")
    def _compute_draft_orders(self):
        for wizard in self:
            orders = (
                wizard.session_id._get_closing_draft_orders()
                if wizard.session_id
                else self.env["pos.order"]
            )
            wizard.draft_order_count = len(orders)
            wizard.draft_order_names = ", ".join(orders.mapped("name"))

    def action_close_session(self):
        self.ensure_one()
        if self.env.context.get("discard_draft_orders"):
            self.session_id.discard_draft_orders_for_closing()
        return super().action_close_session()

    def action_close_session_discarding_drafts(self):
        self.ensure_one()
        return self.with_context(discard_draft_orders=True).action_close_session()
