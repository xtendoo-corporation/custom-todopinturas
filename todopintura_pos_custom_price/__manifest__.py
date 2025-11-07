# -*- coding: utf-8 -*-
{
    'name': "Todopintura POS Custom Price",
    'summary': """
        Permite definir precio personalizado al escanear productos en POS
    """,
    'description': """
        Este módulo añade funcionalidad para:
        - Marcar categorías de productos que requieren precio personalizado
        - Al escanear un producto de esa categoría en POS, mostrar diálogo para introducir precio
        - Aplicar el precio introducido
        - Verificar y aplicar descuentos de la lista de precios del cliente si existen
    """,
    'author': "Xtendoo",
    'website': "https://xtendoo.es",
    'category': 'Point of Sale',
    'version': '19.0.1.0.1',
    'depends': [
        'point_of_sale',
        'product',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_custom_price/static/src/js/product_screen.js',
            'todopintura_pos_custom_price/static/src/xml/custom_price_popup.xml',
        ],
    },
    "data": [
        "views/product_category_views.xml",
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

