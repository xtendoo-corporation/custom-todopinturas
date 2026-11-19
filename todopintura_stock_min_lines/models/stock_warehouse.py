# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def _tp_min_get_hub(self):
        """Almacén central (origen de las reposiciones) de la compañía de este almacén."""
        self.ensure_one()
        return self.sudo().search(
            [
                ("tp_is_central_request_hub", "=", True),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

    def _tp_min_orderpoints(self, products=None):
        """Un punto de pedido con mínimo por producto en este almacén (el de mayor mínimo)."""
        self.ensure_one()
        domain = [("warehouse_id", "=", self.id), ("product_min_qty", ">", 0)]
        if products is not None:
            domain.append(("product_id", "in", products.ids))
        result = {}
        for orderpoint in self.env["stock.warehouse.orderpoint"].sudo().search(domain):
            current = result.get(orderpoint.product_id.id)
            if not current or orderpoint.product_min_qty > current.product_min_qty:
                result[orderpoint.product_id.id] = orderpoint
        return result

    def _tp_min_pending_in_qty(self, products, exclude_pickings=None):
        """Cantidad ya en camino hacia este almacén (traslados sin terminar), por producto."""
        self.ensure_one()
        domain = [
            ("product_id", "in", products.ids),
            ("state", "not in", ("done", "cancel")),
            ("location_dest_id", "child_of", self.lot_stock_id.id),
            "|",
            ("location_id.warehouse_id", "!=", self.id),
            ("location_id.warehouse_id", "=", False),
        ]
        if exclude_pickings:
            domain.append(("picking_id", "not in", exclude_pickings.ids))
        pending = {}
        for move in self.env["stock.move"].sudo().search(domain):
            pending[move.product_id.id] = (
                pending.get(move.product_id.id, 0.0) + move.product_uom_qty
            )
        return pending

    def _tp_min_info(self, products, exclude_pickings=None):
        """Por producto: existencias en este almacén, mínimo y cantidad a enviar.

        «A enviar» = mínimo − existencias − lo que ya va en camino (nunca negativo).
        """
        self.ensure_one()
        orderpoints = self._tp_min_orderpoints(products)
        pending = self._tp_min_pending_in_qty(products, exclude_pickings)
        info = {}
        for product in products.sudo().with_context(location=self.lot_stock_id.id):
            on_hand = product.qty_available
            orderpoint = orderpoints.get(product.id)
            minimum = orderpoint.product_min_qty if orderpoint else 0.0
            to_send = max(minimum - on_hand - pending.get(product.id, 0.0), 0.0)
            info[product.id] = {
                "on_hand": on_hand,
                "min": minimum,
                "to_send": to_send,
                "below_min": bool(minimum) and on_hand < minimum,
            }
        return info

    def _tp_min_below_min_products(self):
        """Productos con mínimo en este almacén cuyas existencias están por debajo."""
        self.ensure_one()
        products = self.env["product.product"].browse(
            list(self._tp_min_orderpoints().keys())
        ).filtered(lambda p: p.active and p.is_storable)
        info = self._tp_min_info(products)
        return products.filtered(lambda p: info[p.id]["below_min"])
