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
        'point_of_sale',
        'account',
        'pos_conventional_core',
        'pos_conventional_order_barcode',
        'pos_conventional_payment_wizard',
        'pos_conventional_picking_integration',
        'sale_stock',
        'todopintura_administration',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/pos_order_views.xml',
        'views/sale_order_observations_views.xml',
        'views/pos_make_payment_wizard_views.xml',
        'views/credit_cashier_warning_wizard_views.xml',
        'views/stock_quant_pos_views.xml',
        'views/credit_override_wizard_views.xml',
        'views/stock_location_views.xml',
        'report/albaran_receipt.xml',
        'report/report_factura_simplificada_inherit.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'todopintura_extend_pos_conventional/static/src/widgets/**/*',
        ],
        'point_of_sale._assets_pos': [
            'todopintura_extend_pos_conventional/static/src/app/**/*',
            'todopintura_extend_pos_conventional/static/src/xml/pos_receipt_templates.xml',
            'todopintura_extend_pos_conventional/static/src/css/pos_receipt.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

