# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Todopintura Stock Quantity Assign',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Evita el llenado automático de cantidades en pickings de compra y permite escaneo de códigos de barras',
    'author': 'Xtendoo',
    'website': '',
    'license': 'AGPL-3',
    'depends': [
        'stock',
        'purchase_stock',
        'barcodes',
    ],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'todopintura_stock_quantity_assign/static/src/js/barcode_debug.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
