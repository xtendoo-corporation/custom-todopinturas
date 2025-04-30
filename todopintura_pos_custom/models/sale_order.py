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


    @api.model
    def create_sale_with_multiple_pickings_from_pos(self, sale_data):
        """Crea una orden de venta desde el POS con albaranes separados por ubicación"""
        # Extraer datos especiales
        auto_validate = sale_data.pop('auto_validate_picking', False)
        products_by_location = sale_data.pop('products_by_location', {})

        # Crear la orden de venta
        sale_order = self.create(sale_data)

        # Confirmar la venta para crear el albarán inicial
        sale_order.action_confirm()

        # Verificar que hay albaranes y mapeo de productos
        if sale_order.picking_ids and products_by_location:
            # Obtener el albarán original
            original_picking = sale_order.picking_ids[0]

            # Mapeo para nuevos albaranes por ubicación
            pickings_by_location = {}

            # Procesar cada movimiento del albarán original
            moves_to_process = original_picking.move_ids
            for move in list(moves_to_process):
                product_id = move.product_id.id
                location_found = False

                # Buscar en qué ubicación está este producto
                for loc_id_str, product_ids in products_by_location.items():
                    loc_id = int(loc_id_str)
                    if product_id in [int(pid) for pid in product_ids]:
                        location_found = True

                        # Crear nuevo albarán si no existe para esta ubicación
                        if loc_id not in pickings_by_location:
                            new_picking = original_picking.copy({
                                'move_ids': [],
                                'move_line_ids': [],
                                'location_id': loc_id,
                                'origin': original_picking.origin + f" (Ubicación: {loc_id})"
                            })
                            pickings_by_location[loc_id] = new_picking

                        # Mover este movimiento al albarán correspondiente
                        move.picking_id = pickings_by_location[loc_id].id
                        move.location_id = loc_id
                        break

            # Si el albarán original quedó vacío, lo cancelamos
            if not original_picking.move_ids:
                original_picking.action_cancel()

            # Procesar todos los albaranes
            if auto_validate:
                for picking in sale_order.picking_ids.filtered(lambda p: p.state != 'cancel'):
                    picking.action_assign()

                    # Asignar cantidades a mover
                    for move in picking.move_ids:
                        if move.state not in ('done', 'cancel'):
                            if hasattr(move, 'quantity'):
                                move.quantity = move.product_uom_qty

                    # Validar albarán
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
