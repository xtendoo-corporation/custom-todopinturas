# -*- coding: utf-8 -*-
{
    'name': 'Todopintura - Extend POS Conventional (Rutas)',
    'summary': 'Permite seleccionar rutas en pedidos POS y líneas',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'LGPL-3',
    'depends': [
        'pos_conventional',
        'stock',
        'sale_stock',
    ],
    'data': [
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

