from odoo import models, api, fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create_sale_from_pos(self, sale_data):
        """Crea una orden de venta desde el POS y valida el albarán"""
        # Extraer y eliminar flags
        auto_validate = sale_data.pop('auto_validate_picking', False)
        custom_location_id = sale_data.pop('custom_location_id', False)

        # Guardar warehouse_id antes de crear la orden
        warehouse_id = sale_data.get('warehouse_id', False)

        # Crear la venta
        sale_order = self.create(sale_data)

        # Confirmar la venta para crear el albarán
        sale_order.action_confirm()

        # Si se requiere validación automática del albarán
        if auto_validate and sale_order.picking_ids:
            for picking in sale_order.picking_ids:
                # Si se especificó una ubicación personalizada, la usamos directamente
                if custom_location_id:
                    custom_location = self.env['stock.location'].browse(custom_location_id)
                    if custom_location.exists():
                        # Actualizar la ubicación de origen en el albarán
                        picking.location_id = custom_location.id
                        # También actualizar la ubicación en los movimientos
                        for move in picking.move_ids:
                            if move.state not in ('done', 'cancel'):
                                move.location_id = custom_location.id
                # Si no hay ubicación personalizada pero sí hay warehouse_id
                elif warehouse_id:
                    warehouse = self.env['stock.warehouse'].browse(warehouse_id)
                    if warehouse.exists():
                        stock_location = warehouse.lot_stock_id
                        if stock_location:
                            picking.location_id = stock_location.id
                            for move in picking.move_ids:
                                if move.state not in ('done', 'cancel'):
                                    move.location_id = stock_location.id

                # Continuar con la reserva y validación
                picking.action_assign()

                # Asignar cantidades en los movimientos principales
                for move in picking.move_ids:
                    if move.state not in ('done', 'cancel'):
                        if hasattr(move, 'quantity'):
                            move.quantity = move.product_uom_qty

                # Validar el albarán
                if picking.state not in ['done', 'cancel']:
                    try:
                        picking.with_context(skip_backorder=True, immediate_transfer=True).button_validate()
                    except UserError as e:
                        _logger.warning(f"Error al validar albarán: {e}")
                        picking.button_validate()

        return {
            'id': sale_order.id,
            'name': sale_order.name,
            'picking_ids': sale_order.picking_ids.ids
        }
