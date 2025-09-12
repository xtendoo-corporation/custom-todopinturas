{
    'name': 'Todo Pintura POS Interface Custom',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Personalización de interfaz POS para Todo Pintura - Contenedor de líneas más pequeño',
    'description': """
        Módulo de personalización para el POS de Todo Pintura.

        Características principales:
        - Oculta el panel de productos para dar más espacio
        - Reduce drásticamente el tamaño del contenedor de líneas de pedidos
        - Hace el contenedor con borde azul más pequeño
        - Optimiza el espacio para una mejor visualización
        - Compatible con Odoo 18
    """,
    'author': 'Todo Pintura',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_interface_custom/static/src/css/pos_custom.css',
            'todopintura_pos_interface_custom/static/src/js/pos_custom.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
