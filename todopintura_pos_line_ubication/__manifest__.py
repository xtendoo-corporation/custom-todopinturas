# -*- coding: utf-8 -*-
{
    'name': "Pos line ubication",
    'summary': """
        Modifica el punto de venta para mostrar la ubicación de la línea
    """,
    'description': """
        Este módulo modifica el punto de venta para mostrar la ubicación de la línea
    """,
    'author': "Abraham (Xtendoo)",
    'website': "",
    'category': 'Point of Sale',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale', 'todopintura_pos_custom'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_line_ubication/static/src/js/control_buttons.js',
            'todopintura_pos_line_ubication/static/src/xml/control_buttons.xml',
            'todopintura_pos_line_ubication/static/src/js/action_pad.js',
            'todopintura_pos_line_ubication/static/src/xml/action_pad.xml',
            'todopintura_pos_line_ubication/static/src/js/location_line_dialog.js',
            'todopintura_pos_line_ubication/static/src/xml/location_line_dialog.xml',
            'todopintura_pos_line_ubication/static/src/js/pos_order_line.js',
            'todopintura_pos_line_ubication/static/src/js/orderline.js',
            'todopintura_pos_line_ubication/static/src/xml/orderline.xml',
        ],
    },
    "data": [
    ],
    'license': 'LGPL-3',
}
