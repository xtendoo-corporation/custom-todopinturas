# -*- coding: utf-8 -*-
{
    "name": "Todopintura POS Conventional Deposit",
    "summary": "Selector crédito/depósito para POS convencional",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "todopintura_extend_pos_conventional",
        "pos_conventional_payment_wizard",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/pos_order_views.xml",
        "views/pos_deposit_payment_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "todopintura_pos_conventional_deposit/static/src/js/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}
