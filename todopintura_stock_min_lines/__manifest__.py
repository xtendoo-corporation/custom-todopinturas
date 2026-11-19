# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Todopintura Stock Min Lines",
    "summary": "Transferencias internas: líneas de reposición bajo mínimos con existencias, mínimo y cantidad a enviar",
    "version": "19.0.1.0.0",
    "category": "Inventory",
    "author": "Xtendoo",
    "website": "http://www.xtendoo.es",
    "license": "AGPL-3",
    "depends": ["stock", "xtendoo_stock_barcode"],
    "data": [
        "views/stock_picking_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "todopintura_stock_min_lines/static/src/**/*.js",
            "todopintura_stock_min_lines/static/src/**/*.xml",
        ],
        "web.assets_tests": [
            "todopintura_stock_min_lines/static/tests/tours/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
