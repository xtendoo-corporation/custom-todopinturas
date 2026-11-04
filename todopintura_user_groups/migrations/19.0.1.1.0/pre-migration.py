# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api

from odoo.addons.todopintura_user_groups.hooks import adopt_manual_records


def migrate(cr, version):
    adopt_manual_records(api.Environment(cr, SUPERUSER_ID, {}))
