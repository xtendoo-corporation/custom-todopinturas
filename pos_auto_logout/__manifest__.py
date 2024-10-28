{
    'name': 'POS Auto Logout',
    'version': "17.0.1.0.0",
    'summary': 'POS Auto Logout When pos order done',
    'category': 'Point of Sale',
    'author': 'Abraham Xtendoo',
    'depends': ['point_of_sale', 'hr'],
    'data': [
        'views/hr_employee_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_auto_logout/static/src/js/pos_auto_logout.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
