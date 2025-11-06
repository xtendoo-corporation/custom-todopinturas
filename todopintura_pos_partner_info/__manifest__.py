# -*- coding: utf-8 -*-
{
    'name': "Todopintura POS Partner Info",
    'summary': """
        Gestión de vales y personas asignadas para clientes en POS
    """,
    'description': """
        Este módulo añade funcionalidad para gestionar:
        - Vales de clientes
        - Información de personas asignadas a clientes
        - Diálogo informativo al seleccionar cliente en POS
    """,
    'author': "Xtendoo",
    'website': "https://xtendoo.es",
    'category': 'Point of Sale',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_partner_info/static/src/xml/coupon_and_assigned_people.xml',
            'todopintura_pos_partner_info/static/src/js/coupon_and_assigned_people.js',
            'todopintura_pos_partner_info/static/src/js/pos_store_partner.js',
        ],
    },
    "data": [
        "views/res_partner_views.xml",
    ],
    'license': 'LGPL-3',
}

