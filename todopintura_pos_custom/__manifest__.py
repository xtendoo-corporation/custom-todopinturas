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
            'todopintura_pos_custom/static/src/js/res_partner.js',
            'todopintura_pos_custom/static/src/js/location_selection_dialog.js',
            'todopintura_pos_custom/static/src/xml/location_selection_dialog.xml',
            'todopintura_pos_custom/static/src/js/product_info_popup.js',
            'todopintura_pos_custom/static/src/xml/product_info_popup.xml',
        ],
    },
    'license': 'LGPL-3',
}
