{
    "name": "Todopinturas Stock Barcode",
    "summary": "Solicitudes al almacén central y permisos por almacén asignado",
    "version": "19.0.1.0.0",
    "category": "Inventory",
    "author": "Xtendoo",
    "website": "http://www.xtendoo.es",
    "license": "AGPL-3",
    "depends": [
        "stock",
        "xtendoo_stock_barcode",
        "todopintura_administration",
        "web_responsive",
    ],
    "data": [
        "views/stock_warehouse_views.xml",
        "views/central_request_views.xml",
        "views/stock_picking_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "todopinturas_stock_barcode/static/src/**/*.js",
            "todopinturas_stock_barcode/static/src/**/*.xml",
        ],
    },
    "installable": True,
    "application": True,
}

