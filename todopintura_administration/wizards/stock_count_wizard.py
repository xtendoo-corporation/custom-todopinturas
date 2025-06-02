from odoo import models, fields, api

class StockCountWizard(models.TransientModel):
    _name = 'stock.count.wizard'
    _description = 'Asistente de Conteo de Inventario'

    count_id = fields.Many2one('stock.count', string='Conteo', required=True)
    product_id = fields.Many2one('product.product', string='Producto')
    product_barcode = fields.Char(related='product_id.barcode', string='Código de barras')
    product_default_code = fields.Char(related='product_id.default_code', string='Referencia interna')
    quantity = fields.Float('Unidades', default=1.0, required=True)

    def action_add_product(self):
        self.ensure_one()
        if self.count_id.state != 'in_progress':
            raise ValidationError(_("El conteo debe estar en progreso para añadir productos."))

        # Crear la línea de conteo
        self.env['stock.count.line'].create({
            'count_id': self.count_id.id,
            'product_id': self.product_id.id,
            'quantity': self.quantity,
        })

        # Mantener el wizard abierto con los campos limpios para añadir otro producto
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.count.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_count_id': self.count_id.id},
        }

    def action_pause(self):
        # Cambiamos el estado a pausado y cerramos el wizard
        self.count_id.write({'state': 'in_progress'})
        return {'type': 'ir.actions.act_window_close'}
