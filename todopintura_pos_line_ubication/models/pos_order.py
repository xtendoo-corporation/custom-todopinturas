from odoo import fields, models, api, _
from odoo.exceptions import UserError
from random import randrange
from odoo.exceptions import ValidationError
import logging
from pprint import pformat
_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    state = fields.Selection(selection_add=[
        ('to_credit', 'A crédito'),
    ], ondelete={'to_credit': 'set default'})

    @api.model
    def create_pos_with_multiple_pickings(self, pos_data):
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("Datos recibidos: %s", pos_data)

        try:
            partner_id = pos_data.get('partner_id')
            config_id = pos_data.get('config_id')
            user_id = pos_data.get('user_id')
            lines_data = pos_data.get('lines', [])
            products_by_location = pos_data.get('products_by_location', {})

            if not lines_data:
                raise UserError(_("No se encontraron líneas para crear el pedido POS."))

            # Buscar sesión POS activa - FUNDAMENTAL
            session = self.env['pos.session'].search([
                ('config_id', '=', config_id),
                ('state', '=', 'opened')
            ], limit=1)

            if not session:
                raise UserError(_("No hay una sesión abierta para esta configuración de POS."))

            # Crear el pedido POS primero
            order_vals = {
                'partner_id': partner_id,
                'config_id': config_id,
                'user_id': user_id,
                'session_id': session.id,  # Añadir sesión POS
                'lines': [(0, 0, {
                    'product_id': line['product_id'],
                    'product_uom_qty': line['quantity'],  # Campo corregido
                    'price_unit': line['price_unit'],
                    'discount': line.get('discount', 0.0),
                    'tax_ids': [(6, 0, line.get('tax_ids', []))],
                }) for line in lines_data]
            }

            _logger.info("Creando orden con valores: %s", order_vals)
            order = self.create(order_vals)
            _logger.info("Orden creada con ID: %s", order.id)

            # Verificar picking_type
            picking_type = self.env['pos.config'].browse(config_id).picking_type_id
            _logger.info("Picking type: %s (ID: %s)", picking_type.name if picking_type else None,
                         picking_type.id if picking_type else None)

            if not picking_type:
                raise UserError(_("La configuración del POS no tiene tipo de picking definido."))

            # Procesar cada ubicación
            for location_id_str, product_list in products_by_location.items():
                _logger.info("Procesando ubicación %s con productos: %s", location_id_str, product_list)
                location_id = int(location_id_str)

                # Verificar que la ubicación existe
                location = self.env['stock.location'].browse(location_id).exists()
                if not location:
                    _logger.error("Ubicación %s no existe", location_id)
                    raise UserError(_("La ubicación %s no existe") % location_id)

                # Verificar destino
                if not picking_type.default_location_dest_id:
                    _logger.error("No se definió ubicación destino en el tipo de picking")
                    raise UserError(_("No se definió ubicación destino en el tipo de picking"))

                # Procesar productos para esta ubicación
                move_lines = []
                for product_entry in product_list:
                    try:
                        product_id = product_entry['id']
                        quantity = product_entry['quantity']
                        product = self.env['product.product'].browse(product_id).exists()

                        if not product:
                            _logger.error("Producto %s no existe", product_id)
                            raise UserError(_("El producto %s no existe") % product_id)

                        _logger.info("Añadiendo producto %s (%s) con cantidad %s",
                                     product.id, product.display_name, quantity)

                        move_lines.append((0, 0, {
                            'name': product.display_name,
                            'product_id': product.id,
                            'product_uom_qty': quantity,
                            'product_uom': product.uom_id.id,
                            'location_id': location_id,
                            'location_dest_id': picking_type.default_location_dest_id.id,
                        }))
                    except (ValueError, KeyError) as e:
                        _logger.error("Error en datos de producto: %s - %s", product_entry, str(e))
                        raise UserError(f"Formato incorrecto en datos del producto: {str(e)}")

                if move_lines:
                    picking_vals = {
                        'partner_id': partner_id,
                        'picking_type_id': picking_type.id,
                        'location_id': location_id,
                        'location_dest_id': picking_type.default_location_dest_id.id,
                        'origin': f'POS {order.name}',
                        'move_lines': move_lines,
                    }
                    _logger.info("Creando picking con valores: %s", picking_vals)
                    picking = self.env['stock.picking'].create(picking_vals)
                    _logger.info("Picking creado con ID: %s", picking.id)

            return order.id

        except Exception as e:
            _logger.error("Error detallado: %s", str(e), exc_info=True)
            import traceback
            _logger.error(traceback.format_exc())
            raise UserError(f"Error: {str(e)}")

    @api.model
    def sync_from_ui(self, orders):
        """Create and update Orders from the frontend PoS application."""
        sync_token = randrange(100_000_000)
        _logger.info("PoS synchronisation #%d started for PoS orders references: %s", sync_token,
                     [self._get_order_log_representation(order) for order in orders])

        print("\n==== INICIANDO SINCRONIZACIÓN DE PEDIDOS ====")
        print(f"Token de sincronización: {sync_token}")
        print(f"Cantidad de pedidos a procesar: {len(orders)}")

        order_ids = []
        for order in orders:
            order_log_name = self._get_order_log_representation(order)

            print("\n----- PROCESANDO PEDIDO -----")
            print(f"Referencia: {order_log_name}")
            print(f"ID: {order.get('id')}")
            print(f"Estado en datos JSON: {order.get('state')}")
            print(f"Flag to_credit: {order.get('to_credit')}")
            print(f"Importe total: {order.get('amount_total')}")
            print(f"Importe pagado: {order.get('amount_paid')}")

            _logger.debug("PoS synchronisation #%d processing order %s order full data: %s", sync_token, order_log_name,
                          pformat(order))

            if len(self._get_refunded_orders(order)) > 1:
                print("ERROR: Intento de reembolsar productos de diferentes pedidos")
                raise ValidationError(_('You can only refund products from the same order.'))

            existing_order = self._get_open_order(order)
            print(f"¿Existe pedido previo?: {bool(existing_order)}")
            print(f"Estado pedido existente: {existing_order.state if existing_order else 'N/A'}")

            # Verificar si es un pedido a crédito directamente de los datos enviados
            is_to_credit = order.get('to_credit', False) or order.get('state') == 'to_credit'
            print(f"¿Es pedido a crédito?: {is_to_credit}")

            if existing_order and existing_order.state == 'to_credit':
                print("CASO 1: Actualizando pedido existente en estado to_credit")
                order_ids.append(self._process_order(order, existing_order))
                print(f"ID del pedido procesado: {order_ids[-1]}")
                print(f"Estado después del proceso: {existing_order.state}")
                _logger.info("PoS synchronisation #%d order %s updated pos.order #%d", sync_token, order_log_name,
                             order_ids[-1])
                # Forzar la creación del albarán para órdenes en estado to_credit
                updated_order = self.browse(order_ids[-1])
                print(f"¿Tiene albaranes asociados?: {bool(updated_order.picking_ids)}")
                print(f"Cantidad de albaranes: {len(updated_order.picking_ids)}")

            elif existing_order and existing_order.state == 'draft':
                print("CASO 2: Actualizando pedido existente en estado draft")
                order_ids.append(self._process_order(order, existing_order))
                print(f"ID del pedido procesado: {order_ids[-1]}")
                _logger.info("PoS synchronisation #%d order %s updated pos.order #%d", sync_token, order_log_name,
                             order_ids[-1])

            elif not existing_order:
                print("CASO 3: Creando nuevo pedido")
                new_order_id = self._process_order(order, False)
                order_ids.append(new_order_id)
                print(f"Nuevo pedido creado con ID: {new_order_id}")
                _logger.info("PoS synchronisation #%d order %s created pos.order #%d", sync_token, order_log_name,
                             order_ids[-1])

                # Verificar si es un pedido a crédito y procesarlo adecuadamente
                if is_to_credit:
                    print("Procesando nuevo pedido como CRÉDITO")
                    created_order = self.browse(new_order_id)
                    print(f"Estado antes de escribir: {created_order.state}")
                    created_order.write({'state': 'to_credit'})
                    print(f"Estado después de escribir: {created_order.state}")

                    # Verificar pagos
                    print(f"Importe pagado: {created_order.amount_paid}")
                    print(f"Importe total: {created_order.amount_total}")
                    if created_order.amount_paid >= created_order.amount_total:
                        print("ATENCIÓN: Pedido a crédito pero está completamente pagado")

                    # Verificar si ya tiene picking asociado antes de crear uno nuevo
                    print(f"¿Tiene albaranes antes de crear?: {bool(created_order.picking_ids)}")
                    if not created_order.picking_ids:
                        print("Creando albarán para pedido a crédito")
                        picking = created_order.with_company(created_order.company_id)._create_order_picking()
                        print(f"Albarán creado: {picking}")
                    print(f"¿Tiene albaranes después?: {bool(created_order.picking_ids)}")
            else:
                print("CASO 4: Pedido existente pero en estado no esperado")
                order_ids.append(existing_order.id)
                print(f"Estado del pedido: {existing_order.state}")
                _logger.info("PoS synchronisation #%d order %s sync ignored for existing PoS order %s (state: %s)",
                             sync_token, order_log_name, existing_order, existing_order.state)

        # Sometime pos_orders_ids can be empty.
        pos_order_ids = self.env['pos.order'].browse(order_ids)
        print(f"\nTotal de pedidos procesados: {len(pos_order_ids)}")
        config_id = pos_order_ids.config_id.ids[0] if pos_order_ids else False
        print(f"Config ID: {config_id}")

        for order in pos_order_ids:
            order._ensure_access_token()
            print(f"Pedido {order.id} - Estado final: {order.state}")
            if not self.env.context.get('preparation'):
                order.config_id.notify_synchronisation(order.config_id.current_session_id.id,
                                                       self.env.context.get('login_number', 0))

        print("==== FIN DE SINCRONIZACIÓN ====\n")
        _logger.info("PoS synchronisation #%d finished", sync_token)
        return pos_order_ids.read_pos_data(orders, config_id)

    def add_payment(self, data):
        print("\n==== INTENTO DE AÑADIR PAGO ====")
        print(f"ID del pedido: {self.id}")
        print(f"Referencia del pedido: {self.pos_reference}")
        print(f"Estado actual: {self.state}")
        print(f"Datos de pago: {data}")

        # Si la orden está en estado to_credit
        if self.state == 'to_credit':
            # Obtener el método de pago
            payment_method = self.env['pos.payment.method'].browse(data.get('payment_method_id'))

            # Verificar si es un método de cuenta de cliente
            # Asumiendo que existe un campo o método para identificar métodos de tipo cuenta de cliente
            if not payment_method.is_customer_account:  # Ajusta este campo según tu modelo
                raise UserError(
                    _("Para órdenes a crédito solo se puede utilizar el método de pago 'Cuenta de Cliente'."))

            print("Pago a crédito con cuenta de cliente validado correctamente")

        print("Procediendo con el pago normal")
        return super(PosOrder, self).add_payment(data)
