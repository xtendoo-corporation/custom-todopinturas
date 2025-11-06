# -*- coding: utf-8 -*-
{
    'name': "Todopintura POS Line Location",
    'summary': """
        Asignación de ubicación específica por línea de pedido en POS
    """,
    'description': """
        Este módulo permite asignar ubicaciones específicas a cada línea de pedido en el POS.
        Funcionalidades:
        - Botón para cambiar ubicación de línea
        - Diálogo de selección de ubicaciones Stock
        - Exportación de ubicación en línea de pedido
        - Visualización de ubicación en líneas
    """,
    'author': "Xtendoo",
    'website': "https://xtendoo.es",
    'category': 'Point of Sale',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale', 'stock'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_line_location/static/src/js/control_buttons.js',
            'todopintura_pos_line_location/static/src/xml/control_buttons.xml',
            'todopintura_pos_line_location/static/src/js/ubication_button.js',
            'todopintura_pos_line_location/static/src/js/action_pad.js',
            'todopintura_pos_line_location/static/src/xml/action_pad.xml',
            'todopintura_pos_line_location/static/src/js/location_selection_dialog.js',
            'todopintura_pos_line_location/static/src/xml/location_selection_dialog.xml',
            'todopintura_pos_line_location/static/src/js/location_line_dialog.js',
            'todopintura_pos_line_location/static/src/xml/location_line_dialog.xml',
            'todopintura_pos_line_location/static/src/js/pos_order_line.js',
            'todopintura_pos_line_location/static/src/js/orderline.js',
            'todopintura_pos_line_location/static/src/js/orderline_wrapper.js',
            'todopintura_pos_line_location/static/src/xml/orderline.xml',
        ],
    },
    "data": [
    ],
    'license': 'LGPL-3',
}

