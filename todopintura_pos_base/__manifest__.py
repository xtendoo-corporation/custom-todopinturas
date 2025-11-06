# -*- coding: utf-8 -*-
{
    'name': "Todopintura POS Base",
    'summary': """
        Configuraciones base y utilidades comunes para POS Todopintura
    """,
    'description': """
        Módulo base que proporciona configuraciones compartidas y funcionalidades
        comunes para todos los módulos de POS de Todopintura.
    """,
    'author': "Xtendoo",
    'website': "https://xtendoo.es",
    'category': 'Point of Sale',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale', 'sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_base/static/src/js/pos_store_base.js',
        ],
    },
    "data": [
        "views/res_config_settings_view.xml",
    ],
    'license': 'LGPL-3',
}

