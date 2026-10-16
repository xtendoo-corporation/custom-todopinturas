# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Todopintura User Groups",
    "summary": "Grupos de permisos por menu de usuario de Todopintura",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "author": "Xtendoo",
    "website": "http://www.xtendoo.es",
    "license": "AGPL-3",
    "depends": [
        "base",
        "stock",
        "sale",
        "sales_team",
        "purchase",
        "account",
        "point_of_sale",
        "todopintura_administration",
        "xtendoo_stock_barcode",
        "account_due_list",
    ],
    "data": [
        "data/res_groups_category.xml",
        "data/res_groups.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
