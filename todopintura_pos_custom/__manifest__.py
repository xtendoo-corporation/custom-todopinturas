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

        ],
    },
    "data": [
        "views/res_config_settings_view.xml",
    ],
    'license': 'LGPL-3',
}
