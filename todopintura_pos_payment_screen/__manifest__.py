# -*- coding: utf-8 -*-
{
    'name': "Pos payment screen",
    'summary': """
        Modifica el punto de venta en la pantalla de pago
    """,
    'description': """
        Modifica el punto de venta en la pantalla de pago
    """,
    'author': "Abraham (Xtendoo)",
    'website': "",
    'category': 'Point of Sale',
    'version': '1.0',
    'depends': ['point_of_sale', 'todopintura_pos_custom', 'todopintura_pos_line_ubication'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_payment_screen/static/src/js/payment_screen.js',
        ],
    },
    'license': 'LGPL-3',
}
