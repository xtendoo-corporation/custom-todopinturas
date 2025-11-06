# -*- coding: utf-8 -*-
{
    'name': "Todopintura POS Delivery Note",
    'summary': """
        Generación de albaranes valorados desde el Punto de Venta
    """,
    'description': """
        Este módulo permite generar albaranes directamente desde el POS:
        - Crear órdenes de venta desde POS con validación automática de albaranes
        - Albaranes valorados (con precios)
        - Soporte para múltiples ubicaciones por albarán
        - Botón de crear albarán en ActionPad
        - Reporte personalizado de albarán
    """,
    'author': "Xtendoo",
    'website': "https://xtendoo.es",
    'category': 'Point of Sale',
    'version': '19.0.1.0.0',
    'depends': [
        'point_of_sale',
        'sale',
        'stock',
        'todopintura_pos_base',
        'todopintura_pos_partner_info',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_delivery_note/static/src/js/action_pad_delivery.js',
        ],
    },
    "data": [
        "views/res_partner_views.xml",
        "views/report_sale_credit_document.xml",
    ],
    'license': 'LGPL-3',
}

