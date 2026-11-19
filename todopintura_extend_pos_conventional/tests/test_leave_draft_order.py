# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import importlib.util
from pathlib import Path

from odoo import Command
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import HttpCase, tagged

MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "migrations"
    / "19.0.1.0.2"
    / "post-migration.py"
)


@tagged("post_install", "-at_install")
class TestAllowDraftOrders(PosConventionalTestCommon):
    """Todopintura permite pedidos en borrador en todos sus TPV."""

    def test_new_pos_config_allows_draft_orders(self):
        config = self.env["pos.config"].create({"name": "TPV borradores nuevo"})
        self.assertTrue(config.allow_draft_orders)

    def test_migration_enables_the_setting_on_existing_configs(self):
        config = self.env["pos.config"].create({"name": "TPV borradores antiguo"})
        config.allow_draft_orders = False
        spec = importlib.util.spec_from_file_location("tp_post_migration", MIGRATION)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.1.0.1")
        config.invalidate_recordset(["allow_draft_orders"])
        self.assertTrue(config.allow_draft_orders)
        self.assertTrue(self.pos_config.allow_draft_orders)


@tagged("post_install", "-at_install")
class TestLeaveDraftOrderTour(PosConventionalTestCommon, HttpCase):
    """En el navegador: salir de un pedido en borrador según el ajuste del TPV."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "pos_can_edit_price" in cls.env.user._fields:
            cls.env.user.pos_can_edit_price = True
        cls.cashier = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Cajero tour borrador",
                    "login": "cajero_tour_borrador",
                    "password": "cajero_tour_borrador",
                    "group_ids": [
                        Command.set(
                            [
                                cls.env.ref("base.group_user").id,
                                cls.env.ref("point_of_sale.group_pos_manager").id,
                            ]
                        )
                    ],
                }
            )
        )

    def _draft_order_url(self, allow):
        self.pos_config.allow_draft_orders = allow
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        return f"/odoo/action-point_of_sale.action_pos_pos_form/{order.id}"

    def test_leaving_a_draft_order_is_allowed(self):
        self.start_tour(
            self._draft_order_url(True),
            "todopintura_leave_draft_order_allowed",
            login="cajero_tour_borrador",
        )

    def test_leaving_a_draft_order_is_blocked_when_the_setting_is_off(self):
        self.start_tour(
            self._draft_order_url(False),
            "todopintura_leave_draft_order_blocked",
            login="cajero_tour_borrador",
        )
