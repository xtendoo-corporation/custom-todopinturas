# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import UserError

CHAIN_SYNC_FIELDS = (
    "xtd_effect_chain_enabled",
    "xtd_chain_receivable_account_id",
    "payment_method_id",
    "fixed_journal_id",
    "variable_journal_ids",
)


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    xtd_effect_on_validate = fields.Boolean(
        string="Contabilizar efecto al validar la factura",
        help=(
            "Al validar una factura con este modo de pago, se crea y "
            "contabiliza automáticamente un pago que reclasifica el importe "
            "de la cuenta de clientes (430) a la cuenta puente del método de "
            "pago. Esta es la ÚNICA pieza que contabiliza un asiento antes "
            "de subir el fichero de la orden de cobro: 'Confirmar pagos' en "
            "la orden nunca contabiliza nada por sí solo, solo cambia de "
            "estado."
        ),
    )
    xtd_manage_effects_discount = fields.Boolean(
        string="Gestionar descuento de efectos",
        help=(
            "Si está marcado, al subir el fichero de la orden de cobro, los "
            "efectos que TODAVÍA NO hayan vencido se reclasifican a la cuenta "
            "de efectos pendientes de vencer y se contabiliza el anticipo del "
            "banco (descuento) en una cuenta de deuda; se liquidan solos en su "
            "fecha de vencimiento. Los efectos ya vencidos en el momento de "
            "subir el fichero no se tocan: siguen el circuito nativo (cuenta "
            "puente del método de pago -> banco, vía conciliación normal)."
        ),
    )
    xtd_pending_effects_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta de efectos pendientes de vencer",
        check_company=True,
        help=(
            "Cuenta (p.ej. 411001) a la que se reclasifican los efectos "
            "todavía no vencidos cuando se suben al banco, en sustitución de "
            "la cuenta puente general del método de pago."
        ),
    )
    xtd_discounted_effects_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta de deudas por efectos descontados",
        check_company=True,
        help=(
            "Cuenta (habitualmente del grupo 520) que recoge la deuda con el "
            "banco mientras el efecto está pendiente de vencer."
        ),
    )
    xtd_preferred_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Línea de método de pago preferida",
        domain="[('payment_method_id', '=', payment_method_id)]",
        check_company=True,
        help=(
            "Cuando una factura usa este modo de pago, su 'Línea de método "
            "de pago preferida' (preferred_payment_method_line_id, la que "
            "decide qué cuenta bancaria se muestra en la factura) se fija a "
            "esta línea. Útil cuando el modo de pago admite varios diarios "
            "(banco_account_link 'variable') y quieres que siempre se "
            "muestre uno concreto, en vez del que el partner tenga por "
            "defecto."
        ),
    )

    xtd_effect_chain_enabled = fields.Boolean(
        string="Gestionar cadena de efectos (generar → subir)",
        help=(
            "Requiere también marcar 'Contabilizar efecto al validar la "
            "factura' (arriba): ese es el paso 1 (430 -> cuenta de efectos "
            "en cartera). Esta cadena añade los pasos 2 y 3, sin distinguir "
            "vencido/no vencido (a diferencia de 'Gestionar descuento de "
            "efectos'):\n"
            "2. Al GENERAR el fichero: cuenta de efectos remesados (debe) / "
            "cuenta de deuda por efectos remesados (haber). 'Confirmar "
            "pagos' en la orden, antes de esto, no contabiliza nada.\n"
            "3. Al SUBIR el fichero con éxito: banco (debe) / cuenta de "
            "efectos en cartera (haber) -- cierra el asiento del paso 1."
        ),
    )
    xtd_chain_receivable_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta de efectos en cartera",
        check_company=True,
        help="Cuenta (p.ej. 441000) a la que se reclasifica el 430 al "
        "validar la factura (paso 1, campo 'Contabilizar efecto al validar "
        "la factura'). Se copia automáticamente a la línea de método de "
        "pago correspondiente en cuanto la guardas aquí -- no hace falta ir "
        "a configurar esa línea a mano.",
    )
    xtd_chain_remesado_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta de efectos remesados",
        check_company=True,
        help="Cuenta (p.ej. 4411...) que se debita al generar el fichero.",
    )
    xtd_chain_bank_debt_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta de deuda por efectos remesados",
        check_company=True,
        help="Cuenta (p.ej. 5208...) que se acredita al generar el fichero, "
        "en contrapartida de la cuenta de efectos remesados.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._xtd_sync_chain_receivable_accounts()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(field_name in vals for field_name in CHAIN_SYNC_FIELDS):
            self._xtd_sync_chain_receivable_accounts()
        return res

    @api.constrains("xtd_manage_effects_discount", "xtd_effect_chain_enabled")
    def _xtd_check_effects_mechanism_exclusive(self):
        # xtd_effect_on_validate is deliberately NOT part of this check: the
        # chain's stage 1 (430 -> efectos en cartera) can come from either
        # trigger -- validating the invoice (Giro: xtd_effect_on_validate)
        # or a plain manual "Registrar pago" (Pagaré, with this OFF and the
        # method line's payment_account_id pointing at the same account).
        # Stages 2/3 don't care which one produced the open line they act
        # on.
        for mode in self:
            if mode.xtd_manage_effects_discount and mode.xtd_effect_chain_enabled:
                raise UserError(
                    self.env._(
                        "'Gestionar descuento de efectos' y 'Gestionar"
                        " cadena de efectos' son dos mecanismos alternativos"
                        " para el modo de pago '%s' -- no actives los dos a"
                        " la vez.",
                        mode.display_name,
                    )
                )

    def _xtd_effects_accounts_or_raise(self):
        self.ensure_one()
        if not self.xtd_pending_effects_account_id or not self.xtd_discounted_effects_account_id:
            raise UserError(
                self.env._(
                    "Configura la cuenta de efectos pendientes de vencer y la"
                    " cuenta de efectos descontados en el modo de pago '%s'"
                    " antes de subir la remesa.",
                    self.display_name,
                )
            )
        return self.xtd_pending_effects_account_id, self.xtd_discounted_effects_account_id

    def _xtd_chain_accounts_or_raise(self):
        self.ensure_one()
        if not self.xtd_chain_remesado_account_id or not self.xtd_chain_bank_debt_account_id:
            raise UserError(
                self.env._(
                    "Configura la cuenta de efectos remesados y la cuenta de"
                    " deuda por efectos remesados en el modo de pago '%s'"
                    " antes de generar el fichero.",
                    self.display_name,
                )
            )
        return self.xtd_chain_remesado_account_id, self.xtd_chain_bank_debt_account_id

    def _xtd_effect_on_validate_journal_or_raise(self):
        """The journal to use for the validation-time effect payment
        (xtd_effect_on_validate). Straightforward for a 'fixed' mode; for a
        'variable' one there is no order yet to pick a journal from, so this
        only works when exactly one is allowed."""
        self.ensure_one()
        if self.bank_account_link == "fixed":
            journal = self.fixed_journal_id
            if not journal:
                raise UserError(
                    self.env._(
                        "El modo de pago '%s' no tiene diario de banco fijo"
                        " configurado.",
                        self.display_name,
                    )
                )
            return journal
        if len(self.variable_journal_ids) == 1:
            return self.variable_journal_ids
        raise UserError(
            self.env._(
                "La gestión automática de efectos al validar la factura"
                " necesita un único diario posible para el modo de pago"
                " '%s' (tiene banco_account_link 'variable' con %d"
                " diarios permitidos). Dale un diario fijo, o deja solo uno"
                " en 'Diarios bancarios permitidos'.",
                self.display_name,
                len(self.variable_journal_ids),
            )
        )

    def _xtd_sync_chain_receivable_accounts(self):
        """Push xtd_chain_receivable_account_id down onto the payment method
        line(s) this mode will actually use (its payment_method_id, on
        every journal it allows), so these fields on the payment mode are
        the only place to configure this -- no separate trip to Payment
        Methods needed. Runs automatically on create/write; silently does
        nothing until both the chain is enabled and the account is set."""
        for mode in self:
            if not mode.xtd_effect_chain_enabled or not mode.xtd_chain_receivable_account_id:
                continue
            journals = mode.fixed_journal_id or mode.variable_journal_ids
            if not journals or not mode.payment_method_id:
                continue
            method_lines = self.env["account.payment.method.line"].search(
                [
                    ("payment_method_id", "=", mode.payment_method_id.id),
                    ("journal_id", "in", journals.ids),
                ]
            )
            method_lines.filtered(
                lambda line, acc=mode.xtd_chain_receivable_account_id: (
                    line.payment_account_id != acc
                )
            ).write({"payment_account_id": mode.xtd_chain_receivable_account_id.id})
