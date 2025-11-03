# -*- coding: utf-8 -*-
{
    'name': "POS ASK PIN AND CHROME MODIFICATIONS",
    'summary': """

    """,
    'description': """

    """,
    'author': "Abraham (Xtendoo)",
    'website': "",
    'category': 'Point of Sale',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale', 'l10n_es_pos', 'pos_hr'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_ask_pin_and_chrome/static/src/js/chrome.js',
            'todopintura_ask_pin_and_chrome/static/src/js/pos_router_patch.js',
            'todopintura_ask_pin_and_chrome/static/src/js/popup_no_close_patch.js',
            'todopintura_ask_pin_and_chrome/static/src/js/ask_pin_new_order.js',
        ],
    },
    "data": [

    ],
    'license': 'LGPL-3',
}
