from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError
from datetime import date
import openpyxl
import io

class ImportStockMinWizard(models.TransientModel):
    _name = 'import.stock.min.wizard'
    _description = 'Wizard para importar el stock mín desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)

    def action_import_stock_min(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS o XLSX.")
        if not self.file_name:
            raise UserError("No se detectó el nombre del archivo.")

        data = base64.b64decode(self.file)
        error_log = []
        is_xlsx = self.file_name.lower().endswith('.xlsx')
        is_xls = self.file_name.lower().endswith('.xls')
        if is_xlsx:
            wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
            sheet = wb.active
            nrows = sheet.max_row
            ncols = sheet.max_column
            get_cell = lambda r, c: sheet.cell(row=r + 1, column=c + 1).value
        elif is_xls:
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
            nrows = sheet.nrows
            ncols = sheet.ncols
            get_cell = lambda r, c: sheet.cell(r, c).value
        else:
            raise UserError("Formato de archivo no soportado. Solo se aceptan .xls o .xlsx")

        for row_idx in range(1, nrows):  # Asumiendo la primera fila como cabecera
            try:
                ref = str(int(get_cell(row_idx, 3)))
            except Exception:
                ref = str(get_cell(row_idx, 3))
            try:
                min_qty = int(get_cell(row_idx, 7))
            except Exception:
                min_qty = 0
            try:
                max_qty_cell = get_cell(row_idx, 8)
                max_qty = int(max_qty_cell) if max_qty_cell and str(max_qty_cell).isdigit() else 0
            except Exception:
                max_qty = 0
            try:
                qty_multiple = int(get_cell(row_idx, 5))
            except Exception:
                qty_multiple = 1

            print(f"Fila {row_idx}: ref={ref}, min_qty={min_qty}, max_qty={max_qty}, qty_multiple={qty_multiple}")

            product = self.env['product.product'].search([('default_code', '=', ref)], limit=1)
            if not product:
                error_log.append(f"Producto no encontrado: {ref}")
                continue
            if max_qty < min_qty:
                max_qty = min_qty * 2

            orderpoint_vals = {
                'product_id': product.id,
                'product_min_qty': min_qty,
                'product_max_qty': max_qty,
                'qty_to_order': min_qty / 2,
                'location_id': self.env.ref('stock.stock_location_stock').id,
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

            for month_idx in range(9, ncols):
                try:
                    cell_value = get_cell(row_idx, month_idx)
                    month_qty = int(cell_value) if cell_value is not None and str(cell_value).isdigit() else min_qty
                except Exception:
                    month_qty = min_qty
                if not month_qty:
                    month_qty = min_qty

                month = month_idx - 8
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

        self.error_log = "\n".join(error_log) if error_log else "Importación completada sin errores."
