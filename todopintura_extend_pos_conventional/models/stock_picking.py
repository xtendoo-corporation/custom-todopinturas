from odoo import models
from odoo.tools.float_utils import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_conventional_source_pos_order(self):
        self.ensure_one()
        pos_order = self.pos_order_id
        if not pos_order and self.origin:
            pos_order = self.env["pos.order"].sudo().search(
                [("name", "=", self.origin)], order="id desc", limit=1
            )
        return pos_order

    def _get_conventional_report_aggregated_move(self, aggregated_line):
        self.ensure_one()
        product = aggregated_line.get("product")
        moves = self.move_ids.filtered(lambda move: move.product_id == product)
        if not moves:
            return self.env["stock.move"]
        if len(moves) == 1:
            return moves[0]

        qty = (
            aggregated_line.get("qty_done")
            or aggregated_line.get("quantity")
            or aggregated_line.get("qty_ordered")
        )
        if qty is not None:
            for move in moves:
                if float_compare(
                    move._get_conventional_report_quantity(),
                    qty,
                    precision_rounding=move.product_uom.rounding,
                ) == 0:
                    return move
        return moves[0]

    def _get_conventional_report_totals(self):
        self.ensure_one()
        subtotal = sum(
            move._get_conventional_report_line_total()
            for move in self.move_ids.filtered(lambda move: move.product_uom_qty)
        )
        return {
            "subtotal": subtotal,
            "tax": subtotal * 0.21,
            "total": subtotal * 1.21,
        }


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_conventional_report_source_line(self):
        self.ensure_one()
        if self.sale_line_id:
            return self.sale_line_id

        picking = self.picking_id
        if picking.sale_id:
            sale_lines = picking.sale_id.order_line.filtered(
                lambda line: line.product_id == self.product_id
            )
            if sale_lines:
                return sale_lines[0]

        pos_order = picking._get_conventional_source_pos_order() if picking else False
        if pos_order:
            pos_lines = pos_order.lines.filtered(
                lambda line: line.product_id == self.product_id
            )
            if pos_lines:
                return pos_lines[0]

        return False

    def _get_conventional_report_quantity(self):
        self.ensure_one()
        qty_done = sum(self.move_line_ids.mapped("quantity"))
        return qty_done or self.quantity or self.product_uom_qty

    def _get_conventional_report_price_unit(self):
        self.ensure_one()
        source_line = self._get_conventional_report_source_line()
        return source_line.price_unit if source_line and "price_unit" in source_line._fields else 0.0

    def _get_conventional_report_discount(self):
        self.ensure_one()
        source_line = self._get_conventional_report_source_line()
        return source_line.discount if source_line and "discount" in source_line._fields else 0.0

    def _get_conventional_report_discounted_price(self):
        self.ensure_one()
        price_unit = self._get_conventional_report_price_unit()
        discount = self._get_conventional_report_discount()
        return price_unit * (1 - (discount or 0.0) / 100)

    def _get_conventional_report_line_total(self, quantity=None):
        self.ensure_one()
        qty = quantity if quantity is not None else self._get_conventional_report_quantity()
        return self._get_conventional_report_discounted_price() * qty
