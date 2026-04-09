import logging
from odoo import fields, models
import base64
import xlrd
from odoo.exceptions import UserError
from datetime import date
import openpyxl
import io


_logger = logging.getLogger(__name__)

class ImportStockMinWizard(models.TransientModel):
    _name = 'import.stock.min.wizard'
    _description = 'Wizard para importar el stock mín desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)

    @staticmethod
    def _is_empty_value(value):
        return value is None or (isinstance(value, str) and not value.strip())

    @classmethod
    def _is_empty_row(cls, row):
        return all(cls._is_empty_value(value) for value in row)

    @staticmethod
    def _to_int(value, default=0):
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_ref(value):
        if value is None:
            return False
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return False
        try:
            numeric_value = float(value)
            if numeric_value.is_integer():
                return str(int(numeric_value))
        except (TypeError, ValueError):
            pass
        return str(value).strip()

    def _append_warning(self, error_log, row_idx, message, ref=None, location_name=None):
        detail = f"Fila {row_idx}: {message}"
        if ref:
            detail += f" | Referencia: {ref}"
        if location_name:
            detail += f" | Ubicación: {location_name}"
        error_log.append(detail)
        _logger.warning(detail)

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
            ncols = sheet.max_column
            rows = sheet.iter_rows(min_row=2, max_col=ncols, values_only=True)
        elif is_xls:
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
            ncols = sheet.ncols
            rows = (tuple(sheet.row_values(row_idx, start_colx=0, end_colx=ncols)) for row_idx in range(1, sheet.nrows))
        else:
            raise UserError("Formato de archivo no soportado. Solo se aceptan .xls o .xlsx")

        empty_row_streak = 0
        processed_rows = 0
        warning_count = 0

        _logger.info("Iniciando importación de stock mínimo desde %s", self.file_name)

        for row_idx, row in enumerate(rows, start=2):
            if self._is_empty_row(row):
                empty_row_streak += 1
                if empty_row_streak >= 20:
                    _logger.info("Importación detenida tras %s filas vacías consecutivas en %s", empty_row_streak, self.file_name)
                    break
                continue
            empty_row_streak = 0

            raw_location = row[2] if len(row) > 2 else None
            location_id = self._to_int(raw_location, default=1)

            ref = self._normalize_ref(row[3] if len(row) > 3 else None)
            if not ref:
                continue

            min_qty = self._to_int(row[7] if len(row) > 7 else None, default=0)
            max_qty = self._to_int(row[8] if len(row) > 8 else None, default=0)
            qty_multiple = self._to_int(row[5] if len(row) > 5 else None, default=1) or 1

            processed_rows += 1
            if processed_rows == 1 or processed_rows % 25 == 0:
                _logger.info("Procesadas %s filas útiles de %s (última fila Excel: %s)", processed_rows, self.file_name, row_idx)

            location_name = "WH/Central" if location_id == 1 else f"T{location_id}/Stock"
            location = self.env['stock.location'].search([('complete_name', '=', location_name)], limit=1)
            if not location:
                warning_count += 1
                self._append_warning(error_log, row_idx, "Ubicación no encontrada", ref=ref, location_name=location_name)
                continue

            product = self.env['product.product'].search([('default_code', '=', ref)], limit=1)

            if not product:
                warning_count += 1
                self._append_warning(error_log, row_idx, "Producto no encontrado", ref=ref, location_name=location_name)
                continue
            if max_qty < min_qty:
                warning_count += 1
                self._append_warning(
                    error_log,
                    row_idx,
                    f"Máximo menor que mínimo. Se ajusta automáticamente a {min_qty * 2}",
                    ref=ref,
                    location_name=location_name,
                )
                max_qty = min_qty * 2

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
                ('location_id', '=', location.id),
            ], limit=1)

            if orderpoint:
                orderpoint.write(orderpoint_vals)
            else:
                orderpoint = self.env['stock.warehouse.orderpoint'].create(orderpoint_vals)

            for month_idx in range(9, ncols):
                month_qty = self._to_int(row[month_idx] if len(row) > month_idx else None, default=min_qty)
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

        summary_lines = [
            f"Archivo: {self.file_name}",
            f"Filas útiles procesadas: {processed_rows}",
            f"Incidencias detectadas: {warning_count}",
        ]
        if error_log:
            summary_lines.append("")
            summary_lines.append("Detalle de incidencias:")
            summary_lines.extend(error_log)
        else:
            summary_lines.append("")
            summary_lines.append("Importación completada sin errores.")

        self.error_log = "\n".join(summary_lines)
        _logger.info(
            "Importación de %s finalizada. Filas procesadas: %s. Incidencias: %s",
            self.file_name,
            processed_rows,
            warning_count,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
