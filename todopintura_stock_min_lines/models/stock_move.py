# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    tp_manual_line = fields.Boolean(
        string="Línea añadida al escanear",
        copy=False,
        help="Línea creada porque se escaneó un producto que no estaba en el traslado.",
    )
    tp_dest_qty = fields.Float(
        string="Existencias destino",
        compute="_compute_tp_min_info",
        digits="Product Unit",
        help="Existencias del producto en el almacén de destino del traslado.",
    )
    tp_min_qty = fields.Float(
        string="Mínimo destino",
        compute="_compute_tp_min_info",
        digits="Product Unit",
    )
    tp_to_send = fields.Float(
        string="A enviar",
        compute="_compute_tp_min_info",
        digits="Product Unit",
        help="Mínimo − existencias del destino − lo que ya va en camino.",
    )

    def _compute_tp_min_info(self):
        for move in self:
            move.tp_dest_qty = move.tp_min_qty = move.tp_to_send = 0.0
        by_warehouse = {}
        for move in self.filtered(lambda m: m.product_id and m.location_dest_id.warehouse_id):
            by_warehouse.setdefault(move.location_dest_id.warehouse_id, self.browse())
            by_warehouse[move.location_dest_id.warehouse_id] |= move
        for warehouse, moves in by_warehouse.items():
            info = warehouse._tp_min_info(
                moves.product_id, exclude_pickings=moves.picking_id.filtered("tp_min_replenish")
            )
            for move in moves:
                data = info[move.product_id.id]
                move.tp_dest_qty = data["on_hand"]
                move.tp_min_qty = data["min"]
                move.tp_to_send = data["to_send"]
