# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Alta única de los empleados cajeros del TPV (migración y primera instalación)."""
import logging

_logger = logging.getLogger(__name__)

MODULE = "todopintura_extend_pos_conventional"
FIRST_PIN = 1001  # PIN inicial 1001, 1002...: cada empleado debe cambiarlo


def _cashier_names(cr):
    """Xtendoo, Roque y los comerciales activos (por nombre del usuario)."""
    names = [("employee_pin_xtendoo", "Xtendoo"), ("employee_pin_roque", "Roque")]
    cr.execute(
        """SELECT 1 FROM information_schema.columns
            WHERE table_name = 'res_users' AND column_name = 'is_commercial'"""
    )
    if cr.fetchone():
        cr.execute(
            """SELECT u.id, p.name FROM res_users u
                 JOIN res_partner p ON p.id = u.partner_id
                WHERE u.active AND u.is_commercial ORDER BY p.name"""
        )
        names += [(f"employee_pin_commercial_{uid}", name) for uid, name in cr.fetchall()]
    return names


def create_pin_employees(env):
    """Crea los empleados una sola vez: cada uno queda registrado con un xmlid y,
    si ya existe, no se vuelve a crear."""
    data = env["ir.model.data"].sudo()
    Employee = env["hr.employee"].sudo()
    company = env["res.company"].browse(1) or env.company
    used_pins = set(Employee.search([("pin", "!=", False)]).mapped("pin"))
    next_pin = FIRST_PIN
    created = []
    for xmlid, name in _cashier_names(env.cr):
        if data.search([("module", "=", MODULE), ("name", "=", xmlid)], limit=1):
            continue
        while str(next_pin) in used_pins:
            next_pin += 1
        employee = Employee.create(
            {"name": name, "company_id": company.id, "pin": str(next_pin)}
        )
        used_pins.add(str(next_pin))
        data.create(
            {
                "module": MODULE,
                "name": xmlid,
                "model": "hr.employee",
                "res_id": employee.id,
                "noupdate": True,
            }
        )
        created.append((name, str(next_pin)))
        next_pin += 1
    if created:
        _logger.info(
            "Empleados del TPV creados (PIN inicial, deben cambiarlo): %s",
            ", ".join(f"{name}={pin}" for name, pin in created),
        )
    return created


def clear_user_pos_pins(cr):
    """El PIN del TPV deja de guardarse en el usuario: se descartan los actuales."""
    cr.execute(
        """SELECT 1 FROM information_schema.columns
            WHERE table_name = 'res_users' AND column_name = 'pos_pin'"""
    )
    if cr.fetchone():
        cr.execute("UPDATE res_users SET pos_pin = NULL WHERE pos_pin IS NOT NULL")


def post_init_hook(env):
    create_pin_employees(env)
