{
    "name": "Todo Pintura Sale Session",
    "summary": "Sale Session Todo Pintura",
    "version": "18.0.1.0.0",
    "description": "Sale Session Todo Pintura",
    "company": "Xtendoo",
    "website": "http://www.xtendoo.es",
    'depends': ['sale', 'web'],
    "license": "AGPL-3",
    "data": [
        "views/sale_session_views.xml",
        "views/sale_session_menu.xml",
        'security/ir.model.access.csv',
        "views/sale_session_history_views.xml",
        "wizards/close_sale_session_wizard_views.xml",
        "wizards/open_sale_session_wizard_views.xml",
        "wizards/sale_order_employee_wizard_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'todopintura_sale_session/static/src/views/kanban/kanban_controller.js',
            'todopintura_sale_session/static/src/views/kanban/kanban_controller.xml',
        ],
    },
    "installable": True,
}
