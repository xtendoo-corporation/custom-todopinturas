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
            'todopintura_pos_custom/static/src/js/pos_order.js',
            'todopintura_pos_custom/static/src/js/partner_list.js',
            'todopintura_pos_custom/static/src/xml/partner_list.xml',
            'todopintura_pos_custom/static/src/js/res_partner.js',
            'todopintura_pos_custom/static/src/js/payment_screen.js',
            'todopintura_pos_custom/static/src/js/product_screen.js',
            'todopintura_pos_custom/static/src/js/location_selection_dialog.js',
            'todopintura_pos_custom/static/src/xml/location_selection_dialog.xml',
            'todopintura_pos_custom/static/src/js/coupon_and_assigned_people.js',
            'todopintura_pos_custom/static/src/xml/coupon_and_assigned_people.xml',
            # 'todopintura_pos_custom/static/src/js/select_contact_dialog.js',
            # 'todopintura_pos_custom/static/src/xml/select_contact_dialog.xml',
            'todopintura_pos_custom/static/src/js/product_info_popup.js',
            'todopintura_pos_custom/static/src/xml/product_info_popup.xml',
            'todopintura_pos_custom/static/src/js/partner_line.js',
            'todopintura_pos_custom/static/src/xml/partner_line.xml',
            'todopintura_pos_custom/static/src/js/partner_orders_screen.js',
            'todopintura_pos_custom/static/src/xml/partner_orders_screen.xml',
            'todopintura_pos_custom/static/src/js/navbar.js',
            'todopintura_pos_custom/static/src/xml/navbar.xml',
            'todopintura_pos_custom/static/src/js/custom_price_popup.js',
            'todopintura_pos_custom/static/src/xml/custom_price_popup.xml',
            'todopintura_pos_custom/static/src/js/chrome.js',

        ],
    },
    "data": [
        "views/res_config_settings_view.xml",
        "views/res_partner_views.xml",
        "views/report_sale_credit_document.xml",
        "views/pos_price_change_log.xml",
        "wizards/credit_limit_warning_wizard.xml",
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
}
