# -*- coding: utf-8 -*-
{
    "name": "Todopintura POS Conventional Config User Filter Fix",
    "summary": (
        "Corrige que un admin global con 'Cajas permitidas' restringidas no "
        "pudiera crear (ni releer) cajas de POS nuevas"
    ),
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "pos_conventional_config_user_filter",
    ],
    "data": [
        "security/pos_config_record_rules.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
