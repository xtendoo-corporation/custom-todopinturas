# -*- coding: utf-8 -*-
{
    'name': 'Todopintura - POS Conventional Payment Selection',
    'summary': 'Selección de tipo de documento al pagar en POS Conventional',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'LGPL-3',
    'depends': [
        'todopintura_extend_pos_conventional',
        'pos_conventional_payment_wizard',
        'todopintura_pos_conventional_deposit',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/pos_payment_selection_wizard_views.xml',
        'views/pos_order_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'todopintura_extend_pos_conventional_payment/static/src/js/pos_payment_selection_bypass.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
