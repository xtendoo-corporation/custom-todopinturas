# -*- coding: utf-8 -*-
{
    'name': "Todopintura POS Partner Orders",
    'summary': """
        Pantalla de órdenes de venta pendientes por cliente en POS
    """,
    'description': """
        Este módulo permite visualizar y procesar órdenes de venta pendientes:
        - Pantalla de órdenes pendientes del cliente
        - Selección múltiple de órdenes
        - Agregar órdenes al pedido actual del POS
        - Botón "Ver ventas a crédito" en línea de cliente
    """,
    'author': "Xtendoo",
    'website': "https://xtendoo.es",
    'category': 'Point of Sale',
    'version': '19.0.1.0.0',
    'depends': [
        'point_of_sale',
        'sale',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_partner_orders/static/src/js/partner_orders_screen.js',
            'todopintura_pos_partner_orders/static/src/xml/partner_orders_screen.xml',
            'todopintura_pos_partner_orders/static/src/js/partner_line.js',
            'todopintura_pos_partner_orders/static/src/xml/partner_line.xml',
        ],
    },
    "data": [
    ],
    'license': 'LGPL-3',
}

