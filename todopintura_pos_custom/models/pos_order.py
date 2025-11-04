from odoo import models, api
import logging
import re

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_sale_order_ids_from_note(self):
        """Extrae las IDs de órdenes de venta del campo general_customer_note"""
        if not self.general_customer_note:
            return []

        # Buscar el patrón SALE_ORDERS:1,2,3
        match = re.search(r'SALE_ORDERS:([0-9,]+)', self.general_customer_note)
        if match:
            ids_str = match.group(1)
            return [int(id_str) for id_str in ids_str.split(',') if id_str.strip()]
        return []

    def _create_invoice(self, move_vals):
        """Sobrescribir para vincular las órdenes de venta después de crear la factura"""
        move = super()._create_invoice(move_vals)

        # Obtener las IDs de órdenes de venta desde el campo general_customer_note
        sale_order_ids = self._get_sale_order_ids_from_note()

        if sale_order_ids and move:
            _logger.info(f'[POS ORDER] Vinculando {len(sale_order_ids)} órdenes de venta con factura {move.name}')
            _logger.info(f'[POS ORDER] IDs de órdenes de venta: {sale_order_ids}')

            try:
                sale_orders = self.env['sale.order'].browse(sale_order_ids)

                # Vincular las órdenes de venta con la factura
                for sale_order in sale_orders:
                    if not sale_order.exists():
                        _logger.warning(f'[POS ORDER] Orden de venta {sale_order.id} no existe')
                        continue

                    _logger.info(f'[POS ORDER] Procesando orden {sale_order.name}')

                    # Actualizar la orden de venta para referenciar la factura
                    sale_order.write({
                        'invoice_ids': [(4, move.id)],
                        'invoice_status': 'invoiced'
                    })
                    _logger.info(f'[POS ORDER] ✅ Orden de venta {sale_order.name} marcada como facturada')

                # Actualizar el invoice_origin de la factura
                sale_order_names = sale_orders.mapped('name')
                if move.invoice_origin:
                    move.invoice_origin = f"{move.invoice_origin}, {', '.join(sale_order_names)}"
                else:
                    move.invoice_origin = ', '.join(sale_order_names)

                # Agregar nota en la factura
                note_text = f"Factura generada desde POS para las órdenes de venta: {', '.join(sale_order_names)}"
                if move.narration:
                    move.narration = f"{move.narration}\n\n{note_text}"
                else:
                    move.narration = note_text

                _logger.info(f'[POS ORDER] ✅ Vinculación completada correctamente')
                _logger.info(f'[POS ORDER] invoice_origin: {move.invoice_origin}')

            except Exception as e:
                _logger.error(f'[POS ORDER] ❌ Error al vincular órdenes de venta: {e}', exc_info=True)
        else:
            if not sale_order_ids:
                _logger.info(f'[POS ORDER] No hay órdenes de venta para vincular en pedido {self.name}')

        return move

    def action_pos_order_invoice(self):
        """Sobrescribir para asegurar que las órdenes de venta se vinculan al crear factura manualmente"""
        result = super().action_pos_order_invoice()

        sale_order_ids = self._get_sale_order_ids_from_note()

        if sale_order_ids and self.account_move:
            _logger.info(f'[POS ORDER] Vinculando órdenes de venta en facturación manual')

            sale_orders = self.env['sale.order'].browse(sale_order_ids)

            for sale_order in sale_orders:
                if not sale_order.exists():
                    continue

                if self.account_move not in sale_order.invoice_ids:
                    sale_order.write({
                        'invoice_ids': [(4, self.account_move.id)],
                        'invoice_status': 'invoiced'
                    })
                    _logger.info(f'[POS ORDER] Orden de venta {sale_order.name} vinculada a factura manual')

        return result



