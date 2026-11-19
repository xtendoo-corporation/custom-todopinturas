# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestCloseWithDraftOrdersTour(PosConventionalTestCommon, HttpCase):
    """El popup de cierre del navegador avisa de los borradores y ofrece borrarlos."""

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
                    "name": "Cajero tour cierre",
                    "login": "cajero_tour_cierre",
                    "password": "cajero_tour_cierre",
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

    def _setup_session_with_draft(self):
        session = self._open_session()
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        action = self.env["ir.actions.client"].create(
            {
                "name": "Cierre tour",
                "tag": "pos_conventional_closing_popup",
                "context": str({"session_id": session.id}),
            }
        )
        return session, order, action

    def test_discard_drafts_and_close_from_the_popup(self):
        session, order, action = self._setup_session_with_draft()
        self.start_tour(
            f"/odoo/action-{action.id}",
            "todopintura_closing_discard_draft_orders",
            login="cajero_tour_cierre",
        )
        self.assertFalse(order.exists())
        self.assertEqual(session.state, "closed")

    def test_going_back_keeps_the_drafts_and_the_session(self):
        session, order, action = self._setup_session_with_draft()
        self.start_tour(
            f"/odoo/action-{action.id}",
            "todopintura_closing_keep_draft_orders",
            login="cajero_tour_cierre",
        )
        self.assertTrue(order.exists())
        self.assertNotEqual(session.state, "closed")
