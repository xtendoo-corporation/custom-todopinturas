from odoo import fields, models, api, _
from odoo.tools import format_datetime, formatLang

class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    filter_supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Filtro proveedor",
        help="Only match prices from the selected supplier",
    )

    applied_on = fields.Selection(
        selection_add=[('4_filter_supplier', "Filtro por proveedor")],
        ondelete={'4_filter_supplier': 'set default'}
    )

    display_applied_on = fields.Selection(
        selection_add=[('3_filter_supplier', "Proveedor")],
        ondelete={'3_filter_supplier': 'set default'}
    )

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'filter_supplier_id')
    def _compute_name(self):
        res = super()._compute_name()
        for item in self:
            if item.filter_supplier_id and item.applied_on == '4_filter_supplier':
                item.name = _("Proveedor: %s", item.filter_supplier_id.display_name)
            elif not item.filter_supplier_id and item.applied_on == '4_filter_supplier':
                item.name = _("Todos los proveedores")
        return res

    @api.onchange('display_applied_on')
    def _onchange_display_applied_on(self):
        for item in self:
            if item.display_applied_on == '3_filter_supplier':
                item.update({
                    'applied_on': '4_filter_supplier',
                    'product_id': None,
                    'product_tmpl_id': None,
                    'categ_id': None,
                    'product_uom': None,
                })
            else:
                super(ProductPricelistItem, self)._onchange_display_applied_on()

    @api.onchange('applied_on')
    def _onchange_applied_on(self):
        for item in self:
            if item.applied_on == '4_filter_supplier' and item.display_applied_on != '3_filter_supplier':
                item.display_applied_on = '3_filter_supplier'
            elif item.applied_on != '4_filter_supplier' and item.display_applied_on == '3_filter_supplier':
                # Si cambió applied_on pero display sigue en proveedor, actualizar display
                item.display_applied_on = item.applied_on
