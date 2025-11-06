from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create_sale_from_pos(self, sale_data):
        """Crea una orden de venta desde el POS y valida el albarán automáticamente"""
        # Extraer y eliminar flags
        auto_validate = sale_data.pop('auto_validate_picking', False)
        custom_location_id = sale_data.pop('custom_location_id', False)


        # Extraer ID del empleado cajero
        employee_cashier_id = sale_data.pop('employee_cashier_id', False)

        # Convertir ID de empleado a ID de usuario
        cashier_id = False
        if employee_cashier_id:
            employee = self.env['hr.employee'].browse(employee_cashier_id)
            if employee.exists() and employee.user_id:
                cashier_id = employee.user_id.id
                _logger.info(f"Empleado {employee.name} convertido a usuario {cashier_id}")
                # Asignar el usuario cajero al comercial de la venta
                sale_data['user_id'] = cashier_id
            else:
                _logger.warning(f"No se pudo encontrar usuario para empleado ID {employee_cashier_id}")

        # Guardar warehouse_id antes de crear la orden
        warehouse_id = sale_data.get('warehouse_id', False)

        # Contexto para evitar notificaciones por correo
        no_mail_context = {
            'mail_auto_subscribe_no_notify': True,
            'mail_create_nosubscribe': True,
            'tracking_disable': True,
            'mail_notrack': True,
            'mail_activity_automation_skip': True
        }

        # Si tenemos un cajero específico, creamos el pedido como ese usuario
        if cashier_id:
            sale_order = self.with_user(cashier_id).with_context(**no_mail_context).create(sale_data)
        else:
            sale_order = self.with_context(**no_mail_context).create(sale_data)

        # Confirmar la venta para crear el albarán sin enviar correos
        if cashier_id:
            sale_order.with_user(cashier_id).with_context(**no_mail_context).action_confirm()
        else:
            sale_order.with_context(**no_mail_context).action_confirm()

        # VALIDAR SIEMPRE EL ALBARÁN AUTOMÁTICAMENTE
        if auto_validate and sale_order.picking_ids:
            _logger.info(f"[SALE ORDER] Validando automáticamente {len(sale_order.picking_ids)} albaranes para orden {sale_order.name}")

            for picking in sale_order.picking_ids:
                # Si hay un cajero específico, asignarlo como responsable del albarán
                if cashier_id:
                    picking.user_id = cashier_id
                    picking.write({'user_id': cashier_id})

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
                if cashier_id:
                    picking.with_user(cashier_id).with_context(**no_mail_context).action_assign()
                else:
                    picking.with_context(**no_mail_context).action_assign()

                # Asignar cantidades en los movimientos principales
                for move in picking.move_ids:
                    if move.state not in ('done', 'cancel'):
                        if hasattr(move, 'quantity'):
                            move.quantity = move.product_uom_qty

                # Validar el albarán sin enviar correos
                if picking.state not in ['done', 'cancel']:
                    try:
                        # Si hay un cajero específico, validar el albarán como ese usuario
                        if cashier_id:
                            picking.with_user(cashier_id).with_context(
                                skip_backorder=True,
                                immediate_transfer=True,
                                **no_mail_context
                            ).button_validate()
                        else:
                            picking.with_context(
                                skip_backorder=True,
                                immediate_transfer=True,
                                **no_mail_context
                            ).button_validate()
                    except UserError as e:
                        _logger.warning(f"Error al validar albarán: {e}")
                        if cashier_id:
                            picking.with_user(cashier_id).with_context(**no_mail_context).button_validate()
                        else:
                            picking.with_context(**no_mail_context).button_validate()

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

        # Extraer ID del empleado cajero
        employee_cashier_id = sale_data.pop('employee_cashier_id', False)

        # Convertir ID de empleado a ID de usuario
        cashier_id = False
        if employee_cashier_id:
            employee = self.env['hr.employee'].browse(employee_cashier_id)
            if employee.exists() and employee.user_id:
                cashier_id = employee.user_id.id
                _logger.info(f"Empleado {employee.name} convertido a usuario {cashier_id}")
                # Asignar el usuario cajero al comercial de la venta
                sale_data['user_id'] = cashier_id
            else:
                _logger.warning(f"No se pudo encontrar usuario para empleado ID {employee_cashier_id}")

        # Contexto para evitar notificaciones por correo
        no_mail_context = {
            'mail_auto_subscribe_no_notify': True,
            'mail_create_nosubscribe': True,
            'tracking_disable': True,
            'mail_notrack': True,
            'mail_activity_automation_skip': True
        }

        # Logging para diagnóstico
        _logger.info(f"Productos por ubicación: {products_by_location}")

        # Crear la orden de venta con el usuario cajero si está disponible
        if cashier_id:
            sale_order = self.with_user(cashier_id).with_context(**no_mail_context).create(sale_data)
        else:
            sale_order = self.with_context(**no_mail_context).create(sale_data)

        # Confirmar la venta para crear el albarán inicial sin enviar correos
        if cashier_id:
            sale_order.with_user(cashier_id).with_context(**no_mail_context).action_confirm()
        else:
            sale_order.with_context(**no_mail_context).action_confirm()

        # Verificar si hay mapeo de productos por ubicación y que no esté vacío
        if sale_order.picking_ids and products_by_location:
            # Obtener el albarán original
            original_picking = sale_order.picking_ids[0]

            # Si hay un cajero específico, asignarlo al albarán original
            if cashier_id:
                original_picking.user_id = cashier_id
                original_picking.write({'user_id': cashier_id})

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
                                new_picking_vals = {
                                    'move_ids': [],
                                    'move_line_ids': [],
                                    'location_id': loc_id,
                                    'origin': sale_order.name,
                                    'user_id': cashier_id if cashier_id else False
                                }

                                # Usar contexto sin correo para crear el nuevo albarán
                                if cashier_id:
                                    new_picking = original_picking.with_user(cashier_id).with_context(
                                        **no_mail_context).copy(new_picking_vals)
                                else:
                                    new_picking = original_picking.with_context(**no_mail_context).copy(
                                        new_picking_vals)

                                # Forzar la actualización del usuario responsable
                                if cashier_id:
                                    new_picking.write({'user_id': cashier_id})

                                pickings_by_location[loc_id] = new_picking
                                _logger.info(f"Creado nuevo albarán para ubicación {loc_id}: {new_picking.name}")

                            # Añadir a la lista para mover
                            moves_to_relocate.append((move, loc_id))
                            break

            # Ahora movemos los productos a sus nuevos albaranes
            for move, loc_id in moves_to_relocate:
                if cashier_id:
                    move.with_user(cashier_id).with_context(**no_mail_context).picking_id = pickings_by_location[
                        loc_id].id
                    move.with_user(cashier_id).with_context(**no_mail_context).location_id = loc_id
                else:
                    move.with_context(**no_mail_context).picking_id = pickings_by_location[loc_id].id
                    move.with_context(**no_mail_context).location_id = loc_id
                _logger.info(f"Movido producto {move.product_id.name} al albarán para ubicación {loc_id}")

            # Solo cancelamos el albarán original si TODAS las líneas fueron movidas
            remaining_moves = original_picking.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
            if not remaining_moves and moves_processed:
                _logger.info(f"Cancelando albarán original {original_picking.name} por estar vacío")
                if cashier_id:
                    original_picking.with_user(cashier_id).with_context(**no_mail_context).action_cancel()
                else:
                    original_picking.with_context(**no_mail_context).action_cancel()
            else:
                _logger.info(f"Albarán original {original_picking.name} mantiene {len(remaining_moves)} líneas")

        # Procesar todos los albaranes (tanto si hay múltiples como uno solo)
        if auto_validate:
            for picking in sale_order.picking_ids.filtered(lambda p: p.state != 'cancel'):
                # Asegurar nuevamente que el usuario sea el cajero
                if cashier_id:
                    picking.write({'user_id': cashier_id})
                    picking.with_user(cashier_id).with_context(**no_mail_context).action_assign()
                else:
                    picking.with_context(**no_mail_context).action_assign()

                # Asignar cantidades a mover
                for move in picking.move_ids:
                    if move.state not in ('done', 'cancel'):
                        if hasattr(move, 'quantity'):
                            move.quantity = move.product_uom_qty

                # Validar albarán sin enviar correos
                if picking.state not in ['done', 'cancel']:
                    try:
                        # Si hay un cajero específico, validar el albarán como ese usuario
                        if cashier_id:
                            picking.with_user(cashier_id).with_context(
                                skip_backorder=True,
                                immediate_transfer=True,
                                **no_mail_context
                            ).button_validate()
                        else:
                            picking.with_context(
                                skip_backorder=True,
                                immediate_transfer=True,
                                **no_mail_context
                            ).button_validate()
                    except UserError as e:
                        _logger.warning(f"Error al validar albarán: {e}")
                        if cashier_id:
                            picking.with_user(cashier_id).with_context(**no_mail_context).button_validate()
                        else:
                            picking.with_context(**no_mail_context).button_validate()

        return {
            'id': sale_order.id,
            'name': sale_order.name,
            'picking_ids': sale_order.picking_ids.ids
        }

    def action_confirm(self):
        """Sobreescribe el método de confirmación para validar el límite de crédito"""
        for order in self:
            partner = order.partner_id.commercial_partner_id

            # Verificar si el cliente tiene configurado un límite de crédito
            if partner.use_partner_credit_limit and partner.credit_limit > 0:
                # Calcular el crédito usado (facturas pendientes)
                credit_used = partner.credit

                # Calcular el valor del pedido actual
                order_amount = order.amount_total

                # Verificar si el pedido sobrepasa el límite
                if credit_used + order_amount > partner.credit_limit:
                    # Mostrar wizard de advertencia
                    return {
                        'name': _('Advertencia de Límite de Crédito'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'credit.limit.warning.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_partner_id': partner.id,
                            'default_sale_order_id': order.id,
                            'default_credit_limit': partner.credit_limit,
                            'default_credit_used': credit_used,
                            'default_order_amount': order_amount,
                            'default_total_credit': credit_used + order_amount,
                        }
                    }

        return super(SaleOrder, self).action_confirm()

    @api.model
    def check_credit_limit(self, partner_id, amount_total):
        """Verifica si el cliente ha excedido su límite de crédito"""
        if not partner_id:
            return False

        partner = self.env['res.partner'].browse(partner_id).commercial_partner_id

        # Verificar si el cliente tiene configurado un límite de crédito
        if partner.use_partner_credit_limit and partner.credit_limit > 0:
            # Calcular el crédito usado (facturas pendientes)
            credit_used = partner.credit

            # Verificar si el pedido sobrepasa el límite
            if credit_used + amount_total > partner.credit_limit:
                return {
                    'error': True,
                    'credit_limit_exceeded': True,
                    'partner_name': partner.name,
                    'credit_limit': partner.credit_limit,
                    'credit_used': credit_used,
                    'order_amount': amount_total,
                    'total_credit': credit_used + amount_total
                }

        return False

    @api.model
    def create_credit_sale(self, sale_data):
        """Crea una orden de venta a crédito desde el POS con albarán sin confirmar"""
        # Extraer ID del empleado cajero si existe
        employee_cashier_id = sale_data.pop('employee_cashier_id', False)

        # Convertir ID de empleado a ID de usuario
        cashier_id = False
        if employee_cashier_id:
            employee = self.env['hr.employee'].browse(employee_cashier_id)
            if employee.exists() and employee.user_id:
                cashier_id = employee.user_id.id
                _logger.info(f"Empleado {employee.name} convertido a usuario {cashier_id}")
                # Asignar el usuario cajero al comercial de la venta
                sale_data['user_id'] = cashier_id
            else:
                _logger.warning(f"No se pudo encontrar usuario para empleado ID {employee_cashier_id}")

        # Guardar warehouse_id antes de crear la orden
        warehouse_id = sale_data.get('warehouse_id', False)

        # Contexto para evitar notificaciones por correo
        no_mail_context = {
            'mail_auto_subscribe_no_notify': True,
            'mail_create_nosubscribe': True,
            'tracking_disable': True,
            'mail_notrack': True,
            'mail_activity_automation_skip': True
        }

        # Si tenemos un cajero específico, creamos el pedido como ese usuario
        if cashier_id:
            sale_order = self.with_user(cashier_id).with_context(**no_mail_context).create(sale_data)
        else:
            sale_order = self.with_context(**no_mail_context).create(sale_data)

        # Buscar o crear la etiqueta "Venta a crédito"
        credit_tag = self.env['crm.tag'].search([('name', '=', 'Venta a crédito')], limit=1)
        if not credit_tag:
            credit_tag = self.env['crm.tag'].create({'name': 'Venta a crédito'})

        # Asignar la etiqueta a la venta
        sale_order.tag_ids = [(4, credit_tag.id)]

        # Confirmar la venta para crear el albarán sin enviar correos
        if cashier_id:
            sale_order.with_user(cashier_id).with_context(**no_mail_context).action_confirm()
        else:
            sale_order.with_context(**no_mail_context).action_confirm()

        # Si hay albaranes, asignar usuario pero NO validar
        if sale_order.picking_ids:
            for picking in sale_order.picking_ids:
                # Asignar responsable
                if cashier_id:
                    picking.user_id = cashier_id
                    picking.write({'user_id': cashier_id})

                # Configurar ubicación si hay warehouse_id
                if warehouse_id:
                    warehouse = self.env['stock.warehouse'].browse(warehouse_id)
                    if warehouse.exists():
                        stock_location = warehouse.lot_stock_id
                        if stock_location:
                            picking.location_id = stock_location.id
                            for move in picking.move_ids:
                                if move.state not in ('done', 'cancel'):
                                    move.location_id = stock_location.id

                # Solo reservar productos, no validar el albarán
                if cashier_id:
                    picking.with_user(cashier_id).with_context(**no_mail_context).action_assign()
                else:
                    picking.with_context(**no_mail_context).action_assign()

        return {
            'sale_id': sale_order.id,
            'name': sale_order.name,
            'picking_ids': sale_order.picking_ids.ids
        }

    @api.model
    def get_partner_pending_orders(self, partner_id):
        """Obtiene órdenes de venta del cliente sin albarán confirmado"""
        domain = [
            ('partner_id', '=', partner_id),
            ('state', 'in', ['sale', 'done']),
            ('invoice_status', '!=', 'invoiced'),
        ]

        # Filtrar órdenes que no tienen albaranes confirmados
        orders = self.search(domain)
        pending_orders = []

        for order in orders:
            # Verificar si tiene albaranes sin confirmar
            pickings_confirmed = all(p.state == 'done' for p in order.picking_ids)
            if not pickings_confirmed:
                pending_orders.append({
                    'id': order.id,
                    'name': order.name,
                    'date_order': fields.Datetime.to_string(order.date_order),
                    'amount_total': order.amount_total,
                    'state': order.state,
                    'picking_status': 'pending' if order.picking_ids else 'no_picking'
                })

        return pending_orders

