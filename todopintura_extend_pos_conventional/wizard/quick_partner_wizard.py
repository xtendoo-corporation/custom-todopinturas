# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
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
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Tarifa",
        required=True,
        domain="[('pos_quick_partner_selectable', '=', True)]",
        default=lambda self: self._default_pricelist_id(),
    )

    @api.model
    def _default_pricelist_id(self):
        pricelists = self.env["product.pricelist"].search(
            [("pos_quick_partner_selectable", "=", True)], limit=2
        )
        return pricelists.id if len(pricelists) == 1 else False

    def action_create_partner(self):
        self.ensure_one()
        if self.order_id.state != "draft":
            raise UserError(
                _("Solo se puede asignar un contacto a un pedido en borrador.")
            )
        if not self.pricelist_id.pos_quick_partner_selectable:
            raise UserError(
                _("La tarifa «%s» no está habilitada para clientes creados al vuelo.")
                % self.pricelist_id.display_name
            )
        # El campo cliente del pedido solo admite empresas sin padre
        partner = self.env["res.partner"].create({
            "name": self.name.strip(),
            "street": self.street,
            "phone": self.phone,
            "email": self.email,
            "is_company": True,
            "company_type": "company",
            "property_product_pricelist": self.pricelist_id.id,
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
