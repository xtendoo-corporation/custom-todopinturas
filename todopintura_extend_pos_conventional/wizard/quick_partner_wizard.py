# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class PosConventionalQuickPartnerWizard(models.TransientModel):
    _name = "pos.conventional.quick.partner.wizard"
    _description = "Creación rápida de contacto desde pedido POS convencional"

    order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Pedido POS",
        required=True,
        readonly=True,
    )
    name = fields.Char(string="Nombre", required=True)
    street = fields.Char(string="Dirección")
    phone = fields.Char(string="Teléfono")
    email = fields.Char(string="Correo electrónico")

    def action_create_partner(self):
        self.ensure_one()
        if self.order_id.state != "draft":
            raise UserError(
                _("Solo se puede asignar un contacto a un pedido en borrador.")
            )
        # El campo cliente del pedido solo admite empresas sin padre
        partner = self.env["res.partner"].create({
            "name": self.name.strip(),
            "street": self.street,
            "phone": self.phone,
            "email": self.email,
            "is_company": True,
            "company_type": "company",
        })
        # Asignar por código no dispara los onchange del formulario: hay que
        # aplicar a mano la tarifa del cliente y recalcular las líneas, igual
        # que al elegir el cliente en el campo Cliente.
        order = self.order_id.with_context(
            skip_completeness_check=True, pricelist_update=True
        )
        order.partner_id = partner
        order._onchange_partner_id()
        order._onchange_partner_id_update_pricelist()
        # Cerrar el diálogo basta: el menú de acciones recarga el formulario al
        # cerrarse. soft_reload dispararía el bloqueo de salida de pedidos con líneas.
        return {"type": "ir.actions.act_window_close"}
