import base64
import xlrd
import openpyxl
from odoo import api, fields, models
from odoo.exceptions import UserError
from io import BytesIO

class ImportStockWizard(models.TransientModel):
    _name = 'import.stock.in.hand.wizard'
    _description = 'Wizard para importar existencias desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)

    def action_import_stock_in_hand(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS o XLSX.")

        data = base64.b64decode(self.file)
        error_log = []

        # Detectar el tipo de archivo por la extensión
        if self.file_name and self.file_name.lower().endswith('.xlsx'):
            wb = openpyxl.load_workbook(BytesIO(data), data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
        else:
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
            rows = [sheet.row_values(row_idx) for row_idx in range(1, sheet.nrows)]

        for row_idx, row in enumerate(rows, start=2):
            try:
                ubicacion_num = str(int(row[0]))
                if ubicacion_num == "1":
                    padre_name = "WH"
                    hija_name = "Central"
                else:
                    padre_name = f"WH{ubicacion_num}"
                    hija_name = "Stock"
                # Buscar ubicación padre
                padre = self.env['stock.location'].search([('name', '=', padre_name)], limit=1)
                if not padre:
                    error_log.append(f"Ubicación padre no encontrada: {padre_name}")
                    continue
                # Buscar ubicación hija bajo el padre
                location = self.env['stock.location'].search([
                    ('name', '=', hija_name),
                    ('location_id', '=', padre.id)
                ], limit=1)
                if not location:
                    error_log.append(f"Ubicación hija no encontrada: {padre_name}/{hija_name}")
                    continue

                ref = str(int(row[1]))
                qty_value = row[6]
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
                error_log.append(f"Error en fila {row_idx}: {str(e)}")

        self.error_log = "\n".join(error_log) if error_log else "Importación completada sin errores."
