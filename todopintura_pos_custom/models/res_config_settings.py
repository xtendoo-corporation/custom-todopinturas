from odoo import models, api, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_load_all_pricelists = fields.Boolean(string="Cargar todas las tarifas",
                                             config_parameter="point_of_sale.pos_load_all_pricelists")

    @api.onchange('pos_load_all_pricelists')
    def _onchange_pos_load_all_pricelists(self):
        if self.pos_load_all_pricelists:
            # Cargar todas las listas de precios disponibles en el sistema
            all_pricelists = self.env['product.pricelist'].search([])
            self.pos_available_pricelist_ids = [(6, 0, all_pricelists.ids)]

    def set_values(self):
        """Sobrescribir para aplicar la configuración al guardar"""
        res = super(ResConfigSettings, self).set_values()

        # Si la opción está activada, aplicamos la configuración permanentemente
        if self.pos_load_all_pricelists:
            # Obtener todas las listas de precios
            all_pricelists = self.env['product.pricelist'].search([])

            # Actualizar todas las configuraciones de POS activas
            pos_configs = self.env['pos.config'].search([])
            for pos_config in pos_configs:
                if pos_config.use_pricelist:  # Solo si el POS usa listas de precios
                    pos_config.with_context(from_settings_view=True).write({
                        'available_pricelist_ids': [(6, 0, all_pricelists.ids)]
                    })

        return res
