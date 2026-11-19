# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class PosSessionPinWizard(models.TransientModel):
    """El PIN del TPV es siempre el de un empleado (hr.employee.pin).

    Varios empleados comparten el usuario de la caja: la sesión conserva ese usuario
    y el empleado queda como cajero (session.employee_id → pedido).
    """

    _inherit = "pos.session.pin.wizard"

    pos_pin = fields.Char(string="PIN del empleado")

    def action_validate_pin(self):
        self.ensure_one()
        session = self.session_id
        employee = self.env["hr.employee"]._tp_find_by_pin(
            self.pos_pin, session.company_id, user=session.user_id
        )
        session.sudo().write({"employee_id": employee.id})
        user = session.user_id

        # Cambio de cajero tras una venta
        if self.env.context.get("switch_user_after_sale"):
            return {
                "type": "ir.actions.client",
                "tag": "pos_conventional_new_order",
                "params": {
                    "default_session_id": session.id,
                    "default_user_id": user.id,
                    "default_employee_id": employee.id,
                },
            }

        # Nuevo pedido con PIN obligatorio
        if self.env.context.get("force_new_order_flow"):
            return {
                "type": "ir.actions.act_window",
                "res_model": "pos.order",
                "view_mode": "form",
                "target": "current",
                "context": {
                    "default_session_id": session.id,
                    "default_user_id": user.id,
                    "default_employee_id": employee.id,
                    "pos_conventional_pin_validated": True,
                },
            }

        # Apertura de sesión
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise UserError(
                _("No tiene permisos para abrir una sesión de Punto de Venta.")
            )
        return {
            "type": "ir.actions.client",
            "tag": "pos_conventional_opening_popup",
            "name": _("Control de apertura"),
            "target": "current",
            "context": {
                "session_id": session.id,
                "config_id": session.config_id.id,
            },
        }
