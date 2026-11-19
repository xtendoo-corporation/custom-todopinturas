# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api

from odoo.addons.todopintura_extend_pos_conventional.hooks import (
    clear_user_pos_pins,
    create_pin_employees,
)


def migrate(cr, version):
    """El TPV usa siempre el PIN de empleado: descarta los PIN de usuario y da de alta
    una sola vez a Xtendoo, Roque y los comerciales como empleados."""
    clear_user_pos_pins(cr)
    create_pin_employees(api.Environment(cr, SUPERUSER_ID, {}))
