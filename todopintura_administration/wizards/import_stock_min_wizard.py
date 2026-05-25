import logging
import base64
import io
import unicodedata
from datetime import date

import openpyxl
import xlrd

from odoo import fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class ImportStockMinWizard(models.TransientModel):
    _name = 'import.stock.min.wizard'
    _description = 'Wizard para importar el stock mín desde un archivo XLS'

    _DEFAULT_LAYOUT = {
        'location': 2,
        'ref': 3,
        'qty_multiple': 5,
        'min_qty': 7,
        'max_qty': 20,
        'month_columns': {month: 7 + month for month in range(1, 13)},
    }

    _MONTH_TOKENS = {
        1: ('ENERO', 'ENE'),
        2: ('FEBRE', 'FEBR', 'FEB'),
        3: ('MARZO', 'MAR'),
        4: ('ABRIL', 'ABR'),
        5: ('MAYO', 'MAY'),
        6: ('JUNIO', 'JUN'),
        7: ('JULIO', 'JUL'),
        8: ('AGOST', 'AGO'),
        9: ('SEPBR', 'SEPT', 'SEP'),
        10: ('OCTUB', 'OCT'),
        11: ('NOVBR', 'NOV'),
        12: ('DICBR', 'DIC'),
    }

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )

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

    @staticmethod
    def _normalize_header(value):
        if value is None:
            return ''
        text = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode('ascii')
        return ''.join(char for char in text.upper().strip() if char.isalnum())

    @classmethod
    def _match_month_number(cls, header):
        for month_number, tokens in cls._MONTH_TOKENS.items():
            if any(header.startswith(token) for token in tokens):
                return month_number
        return False

    @classmethod
    def _extract_layout_from_header_row(cls, row):
        normalized_headers = [cls._normalize_header(value) for value in row]
        month_columns = {}
        max_columns = []
        layout = {}

        for index, header in enumerate(normalized_headers):
            if not header:
                continue
            if 'ALMACEN' in header and 'location' not in layout:
                layout['location'] = index
            elif 'NUMERO' in header and 'ref' not in layout:
                layout['ref'] = index
            elif 'UNIDAD' in header and 'qty_multiple' not in layout:
                layout['qty_multiple'] = index
            elif 'MINIMO' in header and 'min_qty' not in layout:
                layout['min_qty'] = index
            elif 'MAXIMO' in header:
                max_columns.append(index)

            month_number = cls._match_month_number(header)
            if month_number and month_number not in month_columns:
                month_columns[month_number] = index

        if len(month_columns) == 12:
            layout['month_columns'] = month_columns
        if max_columns:
            layout['max_qty'] = max_columns[-1]

        required_keys = {'location', 'ref', 'qty_multiple', 'min_qty', 'month_columns', 'max_qty'}
        if required_keys.issubset(layout):
            return layout
        return False

    @classmethod
    def _get_layout(cls, rows):
        for row_index, row in enumerate(rows, start=1):
            layout = cls._extract_layout_from_header_row(row)
            if layout:
                return row_index, layout
        return 1, dict(cls._DEFAULT_LAYOUT)

    def _append_warning(self, error_log, row_idx, message, ref=None, location_name=None):
        detail = f"Fila {row_idx}: {message}"
        if ref:
            detail += f" | Referencia: {ref}"
        if location_name:
            detail += f" | Ubicación: {location_name}"
        error_log.append(detail)
        _logger.warning(detail)

    @classmethod
    def _extract_month_quantities(cls, row, month_columns, default_min_qty):
        month_quantities = {}
        has_date_specific_stock = False
        for month, month_idx in sorted(month_columns.items()):
            raw_value = row[month_idx] if len(row) > month_idx else None
            is_empty = cls._is_empty_value(raw_value)
            month_qty = cls._to_int(raw_value, default=default_min_qty)
            if not month_qty:
                month_qty = default_min_qty
            month_quantities[month] = month_qty
            if not is_empty:
                has_date_specific_stock = True
        return month_quantities, has_date_specific_stock

    @staticmethod
    def _build_month_ranges(month_quantities, year):
        ranges = []
        current_range = None
        ordered_months = sorted(month_quantities.items())
        for month, month_qty in ordered_months:
            start_date = date(year, month, 1)
            end_date = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
            if not current_range or current_range['min_qty'] != month_qty:
                if current_range:
                    ranges.append(current_range)
                current_range = {
                    'min_qty': month_qty,
                    'start_date': start_date,
                    'end_date': end_date,
                }
                continue
            current_range['end_date'] = end_date
        if current_range:
            ranges.append(current_range)
        return ranges

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
            rows = list(sheet.iter_rows(values_only=True))
        elif is_xls:
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
            rows = [tuple(sheet.row_values(row_idx, start_colx=0, end_colx=sheet.ncols)) for row_idx in range(sheet.nrows)]
        else:
            raise UserError("Formato de archivo no soportado. Solo se aceptan .xls o .xlsx")

        header_row_idx, layout = self._get_layout(rows)
        if header_row_idx == 1 and layout == self._DEFAULT_LAYOUT:
            _logger.warning(
                "No se pudo detectar la cabecera del archivo %s. Se usará el mapeo por defecto.",
                self.file_name,
            )
        else:
            _logger.info(
                "Cabecera detectada en la fila %s del archivo %s. Columnas mensuales: %s",
                header_row_idx,
                self.file_name,
                sorted(layout['month_columns'].items()),
            )

        empty_row_streak = 0
        processed_rows = 0
        warning_count = 0

        _logger.info("Iniciando importación de stock mínimo desde %s", self.file_name)

        for row_idx, row in enumerate(rows[header_row_idx:], start=header_row_idx + 1):
            if self._is_empty_row(row):
                empty_row_streak += 1
                if empty_row_streak >= 20:
                    _logger.info("Importación detenida tras %s filas vacías consecutivas en %s", empty_row_streak, self.file_name)
                    break
                continue
            empty_row_streak = 0

            raw_location = row[layout['location']] if len(row) > layout['location'] else None
            if raw_location is None or raw_location == '':
                continue
            try:
                if isinstance(raw_location, float):
                    ubicacion_num = str(int(raw_location))
                elif isinstance(raw_location, int):
                    ubicacion_num = str(raw_location)
                else:
                    ubicacion_num = str(int(float(str(raw_location).strip())))
            except (ValueError, TypeError):
                ubicacion_num = str(raw_location).strip()

            ref = self._normalize_ref(row[layout['ref']] if len(row) > layout['ref'] else None)
            if not ref:
                continue

            min_qty = self._to_int(row[layout['min_qty']] if len(row) > layout['min_qty'] else None, default=0)
            max_qty = self._to_int(row[layout['max_qty']] if len(row) > layout['max_qty'] else None, default=min_qty)
            # La columna 5 del Excel (index en layout 'qty_multiple') también puede contener
            # la cantidad mínima que exige el proveedor. Obtenemos el valor bruto para
            # decidir si actualizar el supplier min_qty, y luego calculamos el qty_multiple
            # como antes (por compatibilidad con el comportamiento previo).
            raw_qty_multiple = row[layout['qty_multiple']] if len(row) > layout['qty_multiple'] else None
            supplier_min_qty = self._to_int(raw_qty_multiple, default=0)
            qty_multiple = self._to_int(raw_qty_multiple, default=1) or 1

            processed_rows += 1
            if processed_rows == 1 or processed_rows % 25 == 0:
                _logger.info("Procesadas %s filas útiles de %s (última fila Excel: %s)", processed_rows, self.file_name, row_idx)

            # Buscar almacén por ID Todopinturas en la compañía seleccionada
            warehouse = self.env['stock.warehouse'].search([
                ('id_todopinturas', '=', ubicacion_num),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if not warehouse:
                # Si el almacén existe en otra compañía, se ignora silenciosamente
                warehouse_any = self.env['stock.warehouse'].search([
                    ('id_todopinturas', '=', ubicacion_num)
                ], limit=1)
                if warehouse_any:
                    continue

                warning_count += 1
                self._append_warning(error_log, row_idx, f"Almacén con ID Todopinturas '{ubicacion_num}' no encontrado.", ref=ref)
                continue

            location = warehouse.lot_stock_id
            if not location:
                warning_count += 1
                self._append_warning(error_log, row_idx, f"El almacén '{warehouse.name}' no tiene ubicación de stock configurada.", ref=ref, location_name=warehouse.name)
                continue

            product = self.env['product.product'].search([('default_code', '=', ref)], limit=1)

            if not product:
                warning_count += 1
                self._append_warning(error_log, row_idx, "Producto no encontrado", ref=ref, location_name=warehouse.name)
                continue
            # Si la columna 5 contiene una cantidad distinta de 0, la usamos para
            # actualizar el campo `min_qty` del proveedor (product.supplierinfo) del
            # producto. Solo actualizamos si existe al menos una línea de proveedor
            # en la ficha del producto; si no existe, registramos una incidencia.
            try:
                if supplier_min_qty:
                    tmpl = product.product_tmpl_id
                    sellers = getattr(tmpl, 'seller_ids', None)
                    if sellers:
                        # Actualizar todas las líneas de proveedor del template
                        for seller in sellers:
                            try:
                                # Escribir min_qty igual a la cantidad mínima indicada (max_qty no existe en product.supplierinfo)
                                write_vals = {'min_qty': supplier_min_qty}
                                seller.write(write_vals)
                            except Exception as e:
                                warning_count += 1
                                self._append_warning(error_log, row_idx, f"Error escribiendo min_qty en proveedor (id {getattr(seller, 'id', 'n/a')}): {e}", ref=ref, location_name=warehouse.name)
                    else:
                        warning_count += 1
                        self._append_warning(error_log, row_idx, "No hay proveedores en ficha de producto; no se pudo actualizar min_qty proveedor", ref=ref, location_name=warehouse.name)
            except Exception as e:
                warning_count += 1
                self._append_warning(error_log, row_idx, f"Error actualizando min_qty proveedor: {e}", ref=ref, location_name=warehouse.name)
            if max_qty < min_qty:
                warning_count += 1
                self._append_warning(
                    error_log,
                    row_idx,
                    f"Máximo menor que mínimo. Se ajusta automáticamente a {min_qty * 2}",
                    ref=ref,
                    location_name=warehouse.name,
                )
                max_qty = min_qty * 2

            orderpoint_vals = {
                'product_id': product.id,
                'fixed_product_min_qty': min_qty,
                'fixed_product_max_qty': max_qty,
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

            month_quantities, has_date_specific_stock = self._extract_month_quantities(
                row,
                layout['month_columns'],
                min_qty,
            )

            if not has_date_specific_stock:
                orderpoint.stock_min_dates_ids.unlink()
                orderpoint.invalidate_recordset(['product_min_qty', 'product_max_qty'])
                continue

            year = date.today().year
            month_ranges = self._build_month_ranges(month_quantities, year)
            orderpoint.stock_min_dates_ids.unlink()
            for range_vals in month_ranges:
                # Crear también el campo max_qty en stock.min.dates igual al min_qty
                self.env['stock.min.dates'].create({
                    'min_qty': range_vals['min_qty'],
                    'max_qty': range_vals['min_qty'],
                    'start_date': range_vals['start_date'],
                    'end_date': range_vals['end_date'],
                    'orderpoint_id': orderpoint.id,
                })

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
