from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError

class ImportStockWizard(models.TransientModel):
    _name = 'import.stock.in.hand.wizard'
    _description = 'Wizard para importar existencias desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)

    def action_import_stock_in_hand(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS.")

        data = base64.b64decode(self.file)
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)

        error_log = []
        for row_idx in range(1, sheet.nrows):
            try:
                ubication = str(int(sheet.cell(row_idx, 0).value))
                location_name = f"Tienda {ubication}"
                location = self.env['stock.location'].search([('name', '=', location_name)], limit=1)
                if not location:
                    parent_location = self.env.ref('stock.stock_location_stock')
                    location = self.env['stock.location'].create({
                        'name': location_name,
                        'location_id': parent_location.id,
                        'usage': 'internal',
                    })
                ref = str(int(sheet.cell(row_idx, 1).value))

                qty_value = sheet.cell(row_idx, 6).value
                if isinstance(qty_value, str):
                    qty_value = qty_value.strip()
                    if not qty_value:
                        continue

                try:
                    qty_available = int(float(qty_value))
                except (ValueError, TypeError):
                    continue

                product = self.env['product.product'].search([('default_code', '=', ref)], limit=1)
                if not product:
                    error_log.append(f"Producto no encontrado: {ref}")
                    continue

                quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location.id)
                ], limit=1)

                if quant:
                    quant.quantity = qty_available
                else:
                    self.env['stock.quant'].create({
                        'product_id': product.id,
                        'location_id': location.id,
                        'quantity': qty_available,
                    })
            except Exception as e:
                error_log.append(f"Error en fila {row_idx + 1}: {str(e)}")

        if error_log:
            self.error_log = "\n".join(error_log)
        else:
            self.error_log = "Importación completada sin errores."

