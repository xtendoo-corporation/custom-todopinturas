{
    'name': 'POS Auto Logout',
    'version': "17.0.1.0.0",
    'summary': 'POS Auto Logout When pos order done',
    'category': 'Point of Sale',
    'author': 'Abraham Xtendoo',
    'depends': ['point_of_sale'],
    'data': [
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_auto_logout/static/src/js/receipt_screen.js',
        ],
    },
    'installable': True,
    'application': False,
}
