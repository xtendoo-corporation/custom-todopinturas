{
    "name": "Todopintura Client Importer",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Importador de clientes desde archivos Excel de Todopintura",
    "author": "Xtendoo, Tecnativa",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/todopintura_security.xml",
        "views/todopintura_import_views.xml",
        "views/res_partner_todopintura_views.xml",
    ],
    "external_dependencies": {
        "python": ["openpyxl"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
