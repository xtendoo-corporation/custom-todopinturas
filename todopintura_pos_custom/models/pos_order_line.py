from odoo import fields, models, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    location_id = fields.Many2one(
        'stock.location',
        string='Ubicación',
        domain=[('usage', '=', 'internal')],
        help='Ubicación de inventario específica para esta línea de pedido'
    )

    def _export_for_ui(self):
        """Exporta los datos de ubicación para la interfaz de usuario"""
        result = super()._export_for_ui()
        result['location_id'] = self.location_id.id if self.location_id else False
        result['location_name'] = self.location_id.display_name if self.location_id else False
        return result

    def _prepare_base_line_for_taxes_computation(self):
        """Mantiene la compatibilidad con el cálculo de impuestos"""
        result = super()._prepare_base_line_for_taxes_computation()
        return result

    def _get_stock_moves_to_consider(self, stock_moves, product):
        """Filtra movimientos por ubicación si está definida"""
        moves = super()._get_stock_moves_to_consider(stock_moves, product)
        if self.location_id:
            moves = moves.filtered(lambda m: m.location_id.id == self.location_id.id)
        return moves
