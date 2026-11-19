# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestCloseWithDraftOrders(PosConventionalTestCommon):
    """Cierre de caja con pedidos en borrador: aviso y opción de borrarlos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "pos_can_edit_price" in cls.env.user._fields:
            cls.env.user.pos_can_edit_price = True

    def _draft_with_line(self, session):
        order = self._make_draft_order(session, partner=self.partner)
        self._add_line(order)
        return order

    def test_draft_orders_are_listed_for_the_warning(self):
        session = self._open_session()
        draft = self._draft_with_line(session)
        listed = session.get_draft_orders_for_closing()
        self.assertEqual([row["id"] for row in listed], [draft.id])
        self.assertEqual(listed[0]["lines"], 1)
        self.assertEqual(listed[0]["partner"], self.partner.display_name)

    def test_no_warning_without_draft_orders(self):
        session = self._open_session()
        self.assertEqual(session.get_draft_orders_for_closing(), [])

    def test_drafts_block_the_closing_until_they_are_discarded(self):
        session = self._open_session()
        self._draft_with_line(session)
        self.assertFalse(session.close_session_from_ui([]).get("successful"))
        session.discard_draft_orders_for_closing()
        self.assertFalse(session.get_draft_orders_for_closing())
        self.assertFalse(session._cannot_close_session())

    def test_discard_deletes_only_the_drafts_of_that_session(self):
        session = self._open_session()
        other = self._open_session(self._other_config())
        mine = self._draft_with_line(session)
        theirs = self._draft_with_line(other)
        my_name = mine.name
        names = session.discard_draft_orders_for_closing()
        self.assertEqual(names, [my_name])
        self.assertFalse(mine.exists())
        self.assertTrue(theirs.exists())

    def test_discard_refuses_drafts_with_payments(self):
        session = self._open_session()
        draft = self._draft_with_line(session)
        self.env["pos.payment"].create(
            {
                "pos_order_id": draft.id,
                "amount": 1.0,
                "payment_method_id": self.pos_config.payment_method_ids[:1].id,
            }
        )
        with self.assertRaises(UserError):
            session.discard_draft_orders_for_closing()
        self.assertTrue(draft.exists())

    def test_cashier_without_delete_rights_can_discard_the_drafts(self):
        session = self._open_session()
        draft = self._draft_with_line(session)
        cashier = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Cajero borradores",
                    "login": "cajero_borradores",
                    "group_ids": [Command.set([self.env.ref("point_of_sale.group_pos_user").id])],
                }
            )
        )
        # Las reglas de «cajas permitidas» solo dejan operar las sesiones de sus cajas.
        cashier.allowed_pos_config_ids = [Command.link(self.pos_config.id)]
        session.with_user(cashier).discard_draft_orders_for_closing()
        self.assertFalse(draft.exists())

    def test_closing_wizard_warns_and_discards_the_drafts(self):
        session = self._open_session()
        draft = self._draft_with_line(session)
        wizard = self.env["pos.session.closing.wizard"].create({"session_id": session.id})
        self.assertEqual(wizard.draft_order_count, 1)
        self.assertIn(draft.name, wizard.draft_order_names)
        # El botón normal sigue sin dejar cerrar con borradores...
        with self.assertRaises(UserError):
            wizard.action_close_session()
        # ...y el nuevo los borra antes de cerrar.
        wizard.action_close_session_discarding_drafts()
        self.assertFalse(draft.exists())
        self.assertEqual(session.state, "closed")

    def test_cashier_without_access_to_the_till_cannot_discard_its_drafts(self):
        session = self._open_session()
        draft = self._draft_with_line(session)
        stranger = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Otro cajero",
                    "login": "otro_cajero_borradores",
                    "group_ids": [Command.set([self.env.ref("point_of_sale.group_pos_user").id])],
                }
            )
        )
        with self.assertRaises(AccessError):
            session.with_user(stranger).discard_draft_orders_for_closing()
        self.assertTrue(draft.exists())

    def _other_config(self):
        return self.pos_config.copy({"name": "TPV otra sesión borradores"})
