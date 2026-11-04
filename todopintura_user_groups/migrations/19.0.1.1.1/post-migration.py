# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api

from odoo.addons.todopintura_user_groups.hooks import reset_declared_implied_groups


def migrate(cr, version):
    reset_declared_implied_groups(api.Environment(cr, SUPERUSER_ID, {}))
