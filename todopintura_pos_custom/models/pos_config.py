from odoo import api, models,fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_available_pricelists(self):
        self.ensure_one()
        # Verificar si el parámetro está activo
        load_all_pricelists = self.env['ir.config_parameter'].sudo().get_param("point_of_sale.pos_load_all_pricelists")

        if load_all_pricelists:
            # Si está activo, cargar todas las tarifas de la compañía
            print("*"*50)
            print("Loading all pricelists for the company")
            print(load_all_pricelists)
            return self.env['product.pricelist'].search([
                ('company_id', 'in', [self.company_id.id, False])
            ])
        else:
            # Comportamiento original
            return self.available_pricelist_ids if self.use_pricelist else self.pricelist_id
