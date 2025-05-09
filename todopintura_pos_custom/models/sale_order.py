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

        # Logging para diagnóstico
        _logger.info(f"Productos por ubicación: {products_by_location}")

        # Crear la orden de venta
        sale_order = self.create(sale_data)

        # Confirmar la venta para crear el albarán inicial
        sale_order.action_confirm()

        # Verificar si hay mapeo de productos por ubicación y que no esté vacío
        if sale_order.picking_ids and products_by_location:
            # Obtener el albarán original
            original_picking = sale_order.picking_ids[0]

            # Mapeo para nuevos albaranes por ubicación
            pickings_by_location = {}

            # Procesar cada movimiento del albarán original
            all_moves = list(original_picking.move_ids.filtered(lambda m: m.state not in ['done', 'cancel']))
            moves_processed = False

            # Lista para rastrear los movimientos que deben moverse a otros albaranes
            moves_to_relocate = []
            products_with_location = []

            # Primero identificamos qué productos tienen ubicación asignada
            for loc_id_str, product_ids in products_by_location.items():
                for pid in product_ids:
                    products_with_location.append(int(pid))

            for move in all_moves:
                product_id = move.product_id.id

                # Verificar si este producto tiene ubicación asignada
                if product_id in products_with_location:
                    # Buscar la ubicación específica
                    for loc_id_str, product_ids in products_by_location.items():
                        loc_id = int(loc_id_str)
                        if product_id in [int(pid) for pid in product_ids]:
                            moves_processed = True

                            # Crear nuevo albarán si no existe para esta ubicación
                            if loc_id not in pickings_by_location:
                                new_picking = original_picking.copy({
                                    'move_ids': [],
                                    'move_line_ids': [],
                                    'location_id': loc_id,
                                    'origin': sale_order.name
                                })
                                pickings_by_location[loc_id] = new_picking
                                _logger.info(f"Creado nuevo albarán para ubicación {loc_id}: {new_picking.name}")

                            # Añadir a la lista para mover
                            moves_to_relocate.append((move, loc_id))
                            break

            # Ahora movemos los productos a sus nuevos albaranes
            for move, loc_id in moves_to_relocate:
                move.picking_id = pickings_by_location[loc_id].id
                move.location_id = loc_id
                _logger.info(f"Movido producto {move.product_id.name} al albarán para ubicación {loc_id}")

            # Solo cancelamos el albarán original si TODAS las líneas fueron movidas
            remaining_moves = original_picking.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
            if not remaining_moves and moves_processed:
                _logger.info(f"Cancelando albarán original {original_picking.name} por estar vacío")
                original_picking.action_cancel()
            else:
                _logger.info(f"Albarán original {original_picking.name} mantiene {len(remaining_moves)} líneas")

        # Procesar todos los albaranes (tanto si hay múltiples como uno solo)
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
