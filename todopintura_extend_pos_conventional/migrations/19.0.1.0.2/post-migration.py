# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Todopintura permite pedidos en borrador: activa «Ventas en borrador» en los TPV."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    configs = env["pos.config"].with_context(active_test=False).search(
        [("allow_draft_orders", "!=", True)]
    )
    configs.write({"allow_draft_orders": True})
