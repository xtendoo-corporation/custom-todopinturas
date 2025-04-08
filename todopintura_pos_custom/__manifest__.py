# -*- coding: utf-8 -*-
{
    'name': "POS Default Pricelist Only",
    'summary': """
        Utiliza solo la lista de precios por defecto en el POS
    """,
    'description': """
        Este módulo modifica el punto de venta para utilizar únicamente
        la lista de precios predeterminada configurada en el POS,
        mejorando el rendimiento al eliminar cálculos innecesarios.
    """,
    'author': "Abraham (Xtendoo)",
    'website': "",
    'category': 'Point of Sale',
    'version': '1.0',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_custom/static/src/js/pos_store.js',
            'todopintura_pos_custom/static/src/js/control_buttons.js',
        ],
    },
    'license': 'LGPL-3',
}
