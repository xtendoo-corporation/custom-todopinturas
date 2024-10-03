{
    "name": "Todo Pintura Administration",
    "summary": "Administración de Todo Pintura",
    "version": "17.0.1.0.0",
    "description": "Administración de Todo Pintura",
    "company": "Xtendoo",
    "website": "http://www.xtendoo.es",
    'depends': ['base', 'product', 'contacts'],
    "license": "AGPL-3",
    "data": [
        'wizards/import_contacts_wizard_view.xml',
        'wizards/import_suppliers_wizard_view.xml',
        'wizards/import_products_wizard_view.xml',
        'views/menu.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
}
