# -*- coding: utf-8 -*-
from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_partner_pending_orders(self, partner_id):
        """
        Obtiene las órdenes de venta pendientes de un cliente.
        Una orden está pendiente si:
        - Está confirmada (state = 'sale')
        - No tiene factura pagada completamente
        - Tiene albaranes pendientes o parcialmente entregados
        """
        orders = self.search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'sale'),
        ])

        result = []
        for order in orders:
            # Verificar si tiene albaranes pendientes
            has_pending_delivery = any(
                picking.state not in ['done', 'cancel']
                for picking in order.picking_ids
            )

            # Verificar si tiene facturas pendientes
            has_pending_invoice = any(
                invoice.payment_state != 'paid'
                for invoice in order.invoice_ids
                if invoice.state == 'posted'
            )

            # Incluir si tiene entregas o facturas pendientes
            if has_pending_delivery or has_pending_invoice or not order.invoice_ids:
                order_lines = []
                for line in order.order_line:
                    if line.product_id.type != 'service':  # Excluir servicios
                        order_lines.append({
                            'id': line.id,
                            'product_id': line.product_id.id,
                            'product_name': line.product_id.name,
                            'quantity': line.product_uom_qty,
                            'price_unit': line.price_unit,
                            'price_subtotal': line.price_subtotal,
                        })

                if order_lines:  # Solo incluir si tiene líneas
                    result.append({
                        'id': order.id,
                        'name': order.name,
                        'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                        'amount_total': order.amount_total,
                        'order_line': order_lines,
                    })

        return result

