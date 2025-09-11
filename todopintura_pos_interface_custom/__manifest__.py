{
    'name': 'Todo Pintura POS Interface Custom',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Personalización de la interfaz del POS para Todo Pintura',
    'description': """
        Este módulo personaliza la interfaz del POS para:
        - Ocultar las categorías y productos
        - Ampliar el área del pedido y líneas
        - Mostrar más información del cliente
        - Mejorar los botones de pago
    """,
    'author': 'Todo Pintura',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_interface_custom/static/src/css/pos_custom.css',
            'todopintura_pos_interface_custom/static/src/css/pos_enhanced.css',
            'todopintura_pos_interface_custom/static/src/js/pos_custom.js',
            'todopintura_pos_interface_custom/static/src/js/pos_extended.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
