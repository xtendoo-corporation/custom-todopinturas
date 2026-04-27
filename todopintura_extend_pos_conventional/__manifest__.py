# -*- coding: utf-8 -*-
{
    'name': 'Todopintura - Extend POS Conventional (Recogida entre tiendas)',
    'summary': 'Permite definir por línea la tienda de recogida en pedidos POS',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'LGPL-3',
    'depends': [
        'pos_conventional_core',
        'pos_conventional_payment_wizard',
        'pos_conventional_picking_integration',
        'pos_settle_due',
        'sale_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/pos_order_views.xml',
        'views/pos_payment_views.xml',
        'views/credit_override_wizard_views.xml',
        'report/albaran_receipt.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

