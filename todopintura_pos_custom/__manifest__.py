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
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale', 'l10n_es_pos'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_custom/static/src/js/partner_line.js',
            'todopintura_pos_custom/static/src/xml/partner_line.xml',
            'todopintura_pos_custom/static/src/js/partner_orders_screen.js',
            'todopintura_pos_custom/static/src/xml/partner_orders_screen.xml',
            'todopintura_pos_custom/static/src/js/coupon_and_assigned_people.js',
            'todopintura_pos_custom/static/src/xml/coupon_and_assigned_people.xml',
            'todopintura_pos_custom/static/src/js/pos_store.js',
        ],
    },
    "data": [
        "views/res_config_settings_view.xml",
        "views/report_sale_credit_document.xml",
        "views/res_partner_views.xml",
        "security/ir.model.access.csv",
    ],
    'license': 'LGPL-3',
}
