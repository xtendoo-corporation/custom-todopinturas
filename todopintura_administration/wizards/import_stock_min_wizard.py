from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError
from datetime import date


class ImportStockMinWizard(models.TransientModel):
    _name = 'import.stock.min.wizard'
    _description = 'Wizard para importar el stock mín desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)

    def action_import_stock_min(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS.")

        data = base64.b64decode(self.file)
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)

        error_log = []
        for row_idx in range(1, sheet.nrows):  # Assuming the first row is the header
            ubication = str(int(sheet.cell(row_idx, 2).value))
            ref = str(int(sheet.cell(row_idx, 3).value))
            min_qty = int(sheet.cell(row_idx, 7).value)
            max_qty = int(sheet.cell(row_idx, 8).value) if sheet.cell(row_idx, 8).value and str(
                sheet.cell(row_idx, 8).value).isdigit() else 0
            qty_multiple = int(sheet.cell(row_idx, 5).value)

            product = self.env['product.product'].search([('default_code', '=', ref)], limit=1)
            if not product:
                error_log.append(f"Producto no encontrado: {ref}")
                continue
            if max_qty < min_qty:
                max_qty = min_qty * 2

            location_name = f"Tienda {ubication}"
            location = self.env['stock.location'].search([('name', '=', location_name)], limit=1)
            if not location:
                error_log.append(f"Ubicación no encontrada: {location_name}")
                continue

            if not location :
                orderpoint_vals = {
                    'product_id': product.id,
                    'product_min_qty': min_qty,
                    'product_max_qty': max_qty,
                    'qty_to_order': min_qty / 2,
                    'location_id': self.env.ref('stock.stock_location_stock').id,  # Default location, change if needed
                    'qty_multiple': qty_multiple,
                }
            else:
                orderpoint_vals = {
                    'product_id': product.id,
                    'product_min_qty': min_qty,
                    'product_max_qty': max_qty,
                    'qty_to_order': min_qty / 2,
                    'location_id': location.id,
                    'qty_multiple': qty_multiple,
                }
            orderpoint = self.env['stock.warehouse.orderpoint'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', self.env.ref('stock.stock_location_stock').id),
            ], limit=1)
            if orderpoint:
                orderpoint.write(orderpoint_vals)
            else:
                orderpoint = self.env['stock.warehouse.orderpoint'].create(orderpoint_vals)

            for month_idx in range(9, sheet.ncols):  # Starting from column 8 (January)
                try:
                    cell_value = int(sheet.cell(row_idx, month_idx).value)
                except ValueError:
                    cell_value = min_qty
                print("Cell value: ",cell_value)
                month_qty = int(cell_value)
                print("Month qty: ",month_qty)
                if not month_qty:
                    month_qty = min_qty

                month = month_idx - 8  # Calculate month number (1 for January, 2 for February, etc.)
                year = date.today().year
                start_date = date(year, month, 1)
                end_date = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)

                existing_record = self.env['stock.min.dates'].search([
                    ('start_date', '=', start_date),
                    ('end_date', '=', end_date),
                    ('orderpoint_id', '=', orderpoint.id),
                ], limit=1)

                stock_min_dates_vals = {
                    'min_qty': month_qty,
                    'start_date': start_date,
                    'end_date': end_date,
                    'orderpoint_id': orderpoint.id,
                }

                if existing_record:
                    existing_record.write(stock_min_dates_vals)
                else:
                    self.env['stock.min.dates'].create(stock_min_dates_vals)

        if error_log:
            self.error_log = "\n".join(error_log)
        else:
            self.error_log = "Importación completada sin errores."
