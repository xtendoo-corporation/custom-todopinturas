# -*- coding: utf-8 -*-
{
    'name': "Todopintura POS Credit Sales",
    'summary': """
        Gestión de ventas a crédito con validación de ubicación en POS
    """,
    'description': """
        Este módulo añade funcionalidad para gestionar ventas a crédito:
        - Campo de venta a crédito en clientes
        - Ubicación específica para ventas a crédito
        - Validación de ubicación al seleccionar cliente
        - Bloqueo de venta si la ubicación no coincide
    """,
    'author': "Xtendoo",
    'website': "https://xtendoo.es",
    'category': 'Point of Sale',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale', 'stock'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_credit_sales/static/src/js/pos_store_credit.js',
        ],
    },
    "data": [
        "views/res_partner_views.xml",
    ],
    'license': 'LGPL-3',
}

