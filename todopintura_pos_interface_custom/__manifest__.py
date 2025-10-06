{
    'name': 'Todo Pintura POS Interface Custom',
    'version': '19.0.1.0.0',
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
        - Solo se aplica a usuarios básicos
    """,
    'author': 'Todo Pintura',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'todopintura_pos_interface_custom/static/src/js/custom_pos.js',
            'todopintura_pos_interface_custom/static/src/xml/custom_pos_templates.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
