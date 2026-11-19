# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Todopintura Stock Supplier Receipts",
    "summary": "Entradas: se elige el proveedor y la PDA muestra solo las líneas que esperamos recibir de él",
    "version": "19.0.1.0.0",
    "category": "Inventory",
    "author": "Xtendoo",
    "website": "http://www.xtendoo.es",
    "license": "AGPL-3",
    "depends": ["stock", "xtendoo_stock_barcode", "todopintura_stock_min_lines"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/stock_barcode_supplier_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "todopintura_stock_supplier_receipts/static/src/**/*.js",
            "todopintura_stock_supplier_receipts/static/src/**/*.xml",
        ],
        "web.assets_tests": [
            "todopintura_stock_supplier_receipts/static/tests/tours/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
