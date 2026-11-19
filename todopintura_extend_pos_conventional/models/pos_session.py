# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_stock_location(self):
        result = super()._loader_params_stock_location()
        result["search_params"]["fields"].append("pos_receipt_name")
        return result

    def _loader_params_stock_warehouse(self):
        result = super()._loader_params_stock_warehouse()
        result["search_params"]["fields"].append("lot_stock_id")
        return result

    def _loader_params_pos_order_line(self):
        result = super()._loader_params_pos_order_line()
        result["search_params"]["fields"].append("pickup_warehouse_id")
        return result

    # ---- Pedidos en borrador al cerrar la caja ---------------------------------
    def _get_closing_draft_orders(self):
        """Pedidos en borrador de la sesión (los vacíos ya los cancela el cierre)."""
        self.ensure_one()
        return self.env["pos.order"].sudo().search(
            [("session_id", "=", self.id), ("state", "=", "draft")], order="id"
        )

    def get_draft_orders_for_closing(self):
        """Pedidos en borrador que impedirían cerrar la caja, para avisar al usuario."""
        self.ensure_one()
        self.check_access("read")
        return [
            {
                "id": order.id,
                "name": order.name if order.name and order.name != "/" else _("Pedido nuevo"),
                "partner": order.partner_id.display_name or "",
                "amount_total": order.amount_total,
                "lines": len(order.lines),
            }
            for order in self._get_closing_draft_orders()
        ]

    def discard_draft_orders_for_closing(self):
        """Borra los pedidos en borrador de la sesión para poder cerrar la caja.

        Solo borra borradores de esta sesión y sin pagos registrados: un pedido con
        pagos a medias tiene dinero asociado y debe resolverse a mano. El borrado
        se hace con sudo porque los perfiles de tienda no pueden borrar pedidos.
        """
        self.ensure_one()
        self.check_access("write")
        if self.state == "closed":
            raise UserError(_("Esta sesión ya está cerrada."))
        orders = self._get_closing_draft_orders()
        with_payments = orders.filtered("payment_ids")
        if with_payments:
            raise UserError(
                _(
                    "No se pueden borrar los pedidos en borrador con pagos registrados: "
                    "%s. Finalícelos o cancele sus pagos antes de cerrar la caja.",
                    ", ".join(with_payments.mapped("name")),
                )
            )
        names = orders.mapped("name")
        orders.unlink()
        return names
