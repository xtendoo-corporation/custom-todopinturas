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
            ref = str(int(sheet.cell(row_idx, 1).value))
            print(f"Ref: {ref}")
            qty_available = int(sheet.cell(row_idx, 6).value)
            print(f"Qty Available: {qty_available}")
            product = self.env['product.product'].search([('default_code', '=', ref)], limit=1)
            print(f"Product: {product.name}, Default Code: {product.default_code}, Quantity: {qty_available}")
            if not product:
                error_log.append(f"Producto no encontrado: {ref}")
                continue

            stock_change = self.env['stock.change.product.qty'].create({
                'product_id': product.id,
                'product_tmpl_id': product.product_tmpl_id.id,
                'new_quantity': qty_available,
            })
            print(f"Stock Change Created: {stock_change}")
            stock_change.change_product_qty()
            print(f"Stock Quantity Updated for Product: {product.name}")

        if error_log:
            self.error_log = "\n".join(error_log)
        else:
            self.error_log = "Importación completada sin errores."
