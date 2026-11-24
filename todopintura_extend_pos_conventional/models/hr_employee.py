# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    """El PIN de empleado identifica al cajero en el TPV: no puede repetirse."""

    _inherit = "hr.employee"

    @api.constrains("pin")
    def _check_tp_pin_unique(self):
        for employee in self.filtered("pin"):
            duplicate = self.sudo().search(
                [
                    ("pin", "=", employee.pin),
                    ("id", "!=", employee.id),
                    ("company_id", "in", [employee.company_id.id, False]),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "El PIN ya lo usa el empleado «%s». Cada empleado necesita un "
                        "PIN distinto para identificarse en el TPV.",
                        duplicate.name,
                    )
                )

    @api.model
    def _tp_find_by_pin(self, pin, company):
        """Empleado de la empresa con ese PIN, o error. Cualquier empleado puede
        identificarse en cualquier caja: quien controla el acceso a la caja es el
        usuario con el que se abre la sesión, no el PIN."""
        pin = (pin or "").strip()
        employee = self.env["hr.employee"]
        if pin:
            employee = self.sudo().search(
                [("pin", "=", pin), ("company_id", "in", [company.id, False])],
                limit=1,
            )
        if not employee:
            raise ValidationError(
                _("PIN incorrecto. Compruebe su PIN de empleado e inténtelo de nuevo.")
            )
        return employee
