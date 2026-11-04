# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api

from odoo.addons.todopintura_user_groups.hooks import migrate_legacy_warehouse_field


def migrate(cr, version):
    migrate_legacy_warehouse_field(api.Environment(cr, SUPERUSER_ID, {}))
