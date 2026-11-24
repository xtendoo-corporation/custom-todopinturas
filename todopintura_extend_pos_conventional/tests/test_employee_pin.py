# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import importlib.util
from pathlib import Path

from odoo import Command
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.exceptions import ValidationError
from odoo.tests.common import HttpCase, tagged

from .. import hooks

MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "migrations"
    / "19.0.1.0.3"
    / "post-migration.py"
)


@tagged("post_install", "-at_install")
class TestEmployeePin(PosConventionalTestCommon):
    """El PIN del TPV es siempre el del empleado; varios comparten el usuario."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "pos_can_edit_price" in cls.env.user._fields:
            cls.env.user.pos_can_edit_price = True
        Employee = cls.env["hr.employee"]
        cls.ana = Employee.create({"name": "Ana Cajera", "pin": "4711"})
        cls.luis = Employee.create({"name": "Luis Cajero", "pin": "4712"})

    def _session(self):
        return self._open_session()

    def _wizard(self, session, pin, **context):
        return (
            self.env["pos.session.pin.wizard"]
            .with_context(**context)
            .create({"session_id": session.id, "pos_pin": pin})
        )

    def test_employee_pin_identifies_the_cashier_and_keeps_the_user(self):
        session = self._session()
        user = session.user_id
        action = self._wizard(session, "4711").action_validate_pin()
        self.assertEqual(session.employee_id, self.ana)
        self.assertEqual(session.user_id, user)
        self.assertEqual(action["tag"], "pos_conventional_opening_popup")

    def test_two_employees_share_the_same_user(self):
        session = self._session()
        user = session.user_id
        self._wizard(session, "4711").action_validate_pin()
        self.assertEqual(session.employee_id, self.ana)
        self._wizard(session, "4712").action_validate_pin()
        self.assertEqual(session.employee_id, self.luis)
        self.assertEqual(session.user_id, user)

    def test_new_order_flows_use_the_logged_user_and_set_the_employee(self):
        """El pedido lleva al usuario conectado (no al de la caja) y al empleado."""
        session = self._session()
        box_user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create({"name": "Usuario de la caja", "login": "usuario_caja_pin"})
        )
        session.user_id = box_user
        logged = self.env.user
        self.assertNotEqual(logged, box_user)
        action = self._wizard(
            session, "4712", force_new_order_flow=True
        ).action_validate_pin()
        self.assertEqual(action["context"]["default_user_id"], logged.id)
        self.assertEqual(action["context"]["default_employee_id"], self.luis.id)
        action = self._wizard(
            session, "4711", switch_user_after_sale=True
        ).action_validate_pin()
        self.assertEqual(action["params"]["default_user_id"], logged.id)
        self.assertEqual(action["params"]["default_employee_id"], self.ana.id)
        self.assertEqual(session.user_id, box_user)

    def test_order_form_shows_the_pin_employee(self):
        arch = self.env["pos.order"].get_view(
            self.env.ref("point_of_sale.view_pos_pos_form").id, "form"
        )["arch"]
        self.assertIn('name="employee_id"', arch)

    def test_wrong_empty_or_user_pins_are_rejected(self):
        session = self._session()
        for pin in ("0000", "", "   ", False):
            with self.assertRaises(ValidationError):
                self._wizard(session, pin).action_validate_pin()
        if "pos_pin" in self.env["res.users"]._fields:
            session.user_id.pos_pin = "9999"
            with self.assertRaises(ValidationError):
                self._wizard(session, "9999").action_validate_pin()

    def test_new_orders_carry_the_cashier_of_the_session(self):
        session = self._session()
        self._wizard(session, "4712").action_validate_pin()
        order = self._make_draft_order(session, partner=self.partner)
        self.assertEqual(order.employee_id, self.luis)

    def test_any_employee_can_enter_whatever_the_session_user(self):
        """Ni «Empleados del TPV» ni el enlace de RR. HH. restringen el PIN."""
        session = self._session()
        self._wizard(session, "4711").action_validate_pin()
        self.assertEqual(session.employee_id, self.ana)
        other_box = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create({"name": "Otra caja", "login": "otra_caja_enlazada_pin"})
        )
        linked = self.env["hr.employee"].create(
            {"name": "De otra caja", "pin": "4798", "user_id": other_box.id}
        )
        self._wizard(session, "4798").action_validate_pin()
        self.assertEqual(session.employee_id, linked)

    def test_forms_no_longer_expose_the_relation(self):
        for model, view in (
            ("res.users", "base.view_users_form"),
            ("hr.employee", "hr.view_employee_form"),
        ):
            arch = self.env[model].get_view(self.env.ref(view).id, "form")["arch"]
            self.assertNotIn("pos_employee_ids", arch)
            self.assertNotIn("pos_user_ids", arch)
            self.assertNotIn("Empleados del TPV", arch)

    def test_employee_pin_must_be_unique(self):
        with self.assertRaises(ValidationError):
            self.env["hr.employee"].create({"name": "Repetido", "pin": "4711"})

    def test_user_form_no_longer_has_the_pos_pin_page(self):
        arch = self.env["res.users"].get_view(
            self.env.ref("base.view_users_form").id, "form"
        )["arch"]
        self.assertNotIn("pos_conventional_pin", arch)
        self.assertNotIn("PIN del TPV", arch)

    def test_employees_are_created_only_once(self):
        Employee = self.env["hr.employee"]
        hooks.create_pin_employees(self.env)  # alta (o no-op si la migración ya la hizo)
        for xmlid, name in (
            ("employee_pin_xtendoo", "Xtendoo"),
            ("employee_pin_roque", "Roque"),
        ):
            employee = self.env.ref(f"todopintura_extend_pos_conventional.{xmlid}")
            self.assertEqual(employee.name, name)
            self.assertTrue(employee.pin)
        pins = Employee.search([("pin", "!=", False)]).mapped("pin")
        self.assertEqual(len(pins), len(set(pins)))
        # Otra actualización del módulo: no duplica nada.
        before = Employee.search_count([])
        self.assertEqual(hooks.create_pin_employees(self.env), [])
        self.assertEqual(Employee.search_count([]), before)

    def test_commercials_become_employees(self):
        if "is_commercial" not in self.env["res.users"]._fields:
            self.skipTest("Needs todopintura_user_groups")
        commercial = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Comercial Empleado PIN",
                    "login": "comercial_empleado_pin",
                    "is_commercial": True,
                    "group_ids": [Command.set([self.env.ref("base.group_user").id])],
                }
            )
        )
        hooks.create_pin_employees(self.env)
        self.assertTrue(
            self.env["hr.employee"].search([("name", "=", commercial.name)], limit=1)
        )

    def test_migration_discards_user_pins_and_creates_the_employees(self):
        if "pos_pin" not in self.env["res.users"]._fields:
            self.skipTest("Needs pos_conventional_users_pin")
        self.env.user.pos_pin = "5151"
        self.env.flush_all()
        spec = importlib.util.spec_from_file_location("tp_pin_migration", MIGRATION)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.1.0.2")
        self.env.user.invalidate_recordset(["pos_pin"])
        self.assertFalse(self.env.user.pos_pin)
        self.assertTrue(self.env["hr.employee"].search([("name", "=", "Xtendoo")]))


@tagged("post_install", "-at_install")
class TestEmployeePinTour(PosConventionalTestCommon, HttpCase):
    """En el navegador: el diálogo pide el PIN de empleado y abre el pedido nuevo."""

    def test_employee_pin_dialog_opens_a_new_order(self):
        employee = self.env["hr.employee"].create({"name": "Tour Cajera", "pin": "4711"})
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Cajero tour PIN",
                    "login": "cajero_tour_pin",
                    "password": "cajero_tour_pin",
                    "group_ids": [
                        Command.set(
                            [
                                self.env.ref("base.group_user").id,
                                self.env.ref("point_of_sale.group_pos_manager").id,
                            ]
                        )
                    ],
                }
            )
        )
        session = self._open_session()
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "PIN empleado tour",
                "res_model": "pos.session.pin.wizard",
                "view_mode": "form",
                "target": "new",
                "context": str(
                    {
                        "default_session_id": session.id,
                        "force_new_order_flow": True,
                        "no_cancel": True,
                    }
                ),
            }
        )
        self.start_tour(
            f"/odoo/action-{action.id}",
            "todopintura_employee_pin_new_order",
            login=user.login,
        )
        self.assertEqual(session.employee_id, employee)
