# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    pos_can_manual_product_entry = fields.Boolean(
        string="Puede buscar/escribir productos en TPV",
        default=False,
        help="Si está desmarcado, en las líneas de un pedido de TPV convencional "
        "solo se admiten productos introducidos mediante código de barras. "
        "Si está marcado, el usuario también puede escribir o buscar productos a mano.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["pos_can_manual_product_entry"]
