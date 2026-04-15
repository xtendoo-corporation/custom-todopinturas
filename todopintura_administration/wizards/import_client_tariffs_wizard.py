import logging
import base64
import io

from odoo import fields, models
from odoo.exceptions import UserError, ValidationError

try:
    import xlrd
    from xlrd import xldate_as_datetime
except ImportError:
    xlrd = None
    xldate_as_datetime = None
try:
    import openpyxl
except ImportError:
    openpyxl = None


_logger = logging.getLogger(__name__)

class ImportClientTariffsWizard(models.TransientModel):
    _name = 'import.client.tariffs.wizard'
    _description = 'Wizard to import client tariffs from an XLS or XLSX file'

    file = fields.Binary('Upload XLS or XLSX file', required=True)
    file_name = fields.Char('File name')
    error_log = fields.Text('Errors', readonly=True)

    @staticmethod
    def _cell_to_text(value, default=''):
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    def _safe_int(self, value, field_name, row_number, default=0):
        if value in (None, False, ''):
            return default
        if isinstance(value, str):
            value = value.replace('_', '').strip()
            if not value:
                return default
        if isinstance(value, (int, float)):
            return int(value)
        try:
            return int(float(value))
        except (TypeError, ValueError):
            self._trace_row(row_number, f"valor no numérico en {field_name}: {value!r}", level='warning')
            return None

    def _trace_row(self, excel_row, message, row_data=None, level='info', **context):
        parts = [f"Fila {excel_row}: {message}"]
        parts.extend(f"{key}={value}" for key, value in context.items() if value not in (None, False, ''))
        if row_data is not None:
            parts.append(f"row={row_data}")
        full_message = ' | '.join(parts)
        getattr(_logger, level)(full_message)
        print(full_message, flush=True)
        return full_message

    def _register_row_error(self, errors, excel_row, message, row_data=None, **context):
        full_message = self._trace_row(excel_row, message, row_data=row_data, level='warning', **context)
        errors.append(full_message)

    def _ensure_base_pricelist(self, price_line):
        if not price_line:
            return False
        pricelist_name = f"Tarifa {price_line}"
        pricelist = self.env['product.pricelist'].search([('name', '=', pricelist_name)], limit=1)
        if not pricelist:
            pricelist = self.env['product.pricelist'].create({'name': pricelist_name, 'company_id': False})
            _logger.info("Creada automáticamente la tarifa base %s durante la importación de tarifas de cliente", pricelist_name)
        return pricelist

    def _upsert_pricelist_item(self, errors, excel_row, vals, search_domain=None, client_ref=None, product_code=None, row_data=None):
        if vals.get('base') == 'pricelist' and not vals.get('base_pricelist_id'):
            self._register_row_error(
                errors,
                excel_row,
                "la línea de tarifa usa 'Otra lista de precios' como base pero no tiene tarifa base asignada",
                row_data=row_data,
                client_ref=client_ref,
                product_code=product_code,
                applied_on=vals.get('applied_on'),
            )
            return False

        try:
            pricelist_item = False
            if search_domain:
                pricelist_item = self.env['product.pricelist.item'].search(search_domain, limit=1)
            if pricelist_item:
                pricelist_item.write(vals)
                return pricelist_item
            return self.env['product.pricelist.item'].create(vals)
        except (UserError, ValidationError) as exc:
            self._register_row_error(
                errors,
                excel_row,
                str(exc),
                row_data=row_data,
                client_ref=client_ref,
                product_code=product_code,
                applied_on=vals.get('applied_on'),
            )
        except Exception as exc:
            _logger.exception("Fila %s: error inesperado al guardar línea de tarifa.", excel_row)
            self._register_row_error(
                errors,
                excel_row,
                f"error inesperado al guardar la línea de tarifa: {exc}",
                row_data=row_data,
                client_ref=client_ref,
                product_code=product_code,
                applied_on=vals.get('applied_on'),
            )
        return False

    def action_import_tariffs(self):
        if not self.file:
            raise UserError("Please upload an XLS or XLSX file.")

        data = base64.b64decode(self.file)
        book = None
        ext = ''
        if self.file_name:
            ext = self.file_name.split('.')[-1].lower()
        if not ext or ext not in ['xls', 'xlsx']:
            if data[:2] == b'PK':
                ext = 'xlsx'
            elif data[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                ext = 'xls'
        _logger.info("Importación de tarifas %s: extensión detectada %s", self.file_name, ext)
        sheet = None
        is_xlsx = False
        if ext == 'xlsx':
            if not openpyxl:
                raise UserError("Falta la librería openpyxl para procesar archivos .xlsx. Por favor, instálala.")
            is_xlsx = True
            _logger.info("Importación de tarifas %s: usando openpyxl", self.file_name)
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            sheet = wb.active
        elif ext == 'xls':
            if not xlrd:
                raise UserError("Falta la librería xlrd para procesar archivos .xls. Por favor, instálala.")
            _logger.info("Importación de tarifas %s: usando xlrd", self.file_name)
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
        else:
            raise UserError("Formato de archivo no soportado. Usa .xls o .xlsx")

        errors = []
        if is_xlsx:
            _logger.info("Importación de tarifas %s: procesando filas con openpyxl", self.file_name)
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
            for row_idx, row in enumerate(rows):
                excel_row = row_idx + 2
                self._trace_row(excel_row, "inicio procesamiento", row_data=row)
                # Si la fila está vacía, termina la importación
                if not any(row):
                    self._trace_row(excel_row, "fila vacía detectada. Fin de importación", row_data=row)
                    break
                if len(row) < 14:
                    self._register_row_error(errors, excel_row, "la fila no tiene suficientes columnas para procesarse", row_data=row)
                    continue

                client_ref = self._cell_to_text(row[1])
                provider_ref = f"0{self._cell_to_text(row[2])}" if row[2] else '0'
                product_code = self._cell_to_text(row[3], default='0')
                raw_category = row[4]
                category = self._safe_int(raw_category, 'category', excel_row, default=0)
                if category is None:
                    category = 0
                size = self._cell_to_text(row[5])
                raw_price_line = row[6]
                price_line = self._safe_int(raw_price_line, 'price_line', excel_row, default=0)
                if price_line is None:
                    self._register_row_error(errors, excel_row, f"valor inválido en la columna Línea ({raw_price_line!r}). Fila omitida", row_data=row)
                    continue
                discount = str(float(row[7])) if row[7] and isinstance(row[7], (int, float)) else '0'
                fixed_price = str(float(row[8])) if row[8] and isinstance(row[8], (int, float)) else '0'
                percentage_about_cost = str(-float(row[9])) if row[9] and isinstance(row[9], (int, float)) else '0'
                client = self.env['res.partner'].search([('ref', '=', client_ref)], limit=1)
                provider = self.env['res.partner'].search([('ref', '=', provider_ref)],
                                                          limit=1) if provider_ref != '0777' else None
                self._trace_row(
                    excel_row,
                    "datos principales leídos",
                    client_ref=client_ref,
                    provider_ref=provider_ref,
                    product_code=product_code,
                    price_line=price_line,
                )
                product = self.env['product.template'].search([('default_code', '=', product_code)], limit=1)
                pos_categ = self.env['pos.category'].search([('referencia_todopintura', '=', category)], limit=1)

                # Procesar fechas
                date_start = row[12]
                date_end = row[13]
                try:
                    if book and xldate_as_datetime and isinstance(date_start, float):
                        date_start = xldate_as_datetime(date_start, book.datemode).strftime('%Y-%m-%d')
                    if book and xldate_as_datetime and isinstance(date_end, float):
                        date_end = xldate_as_datetime(date_end, book.datemode).strftime('%Y-%m-%d')
                    if date_start and date_end and (date_end < date_start or date_end == date_start):
                        _logger.warning(
                            "Fila %s: rango de fechas inválido date_start=%s date_end=%s. Se ignoran fechas.",
                            excel_row,
                            date_start,
                            date_end,
                        )
                        date_start = None
                        date_end = None
                except Exception:
                    _logger.exception("Fila %s: error procesando fechas. Se ignoran fechas.", excel_row)
                    date_start = None
                    date_end = None

                # Gestionar categorías
                product_category = None
                provider_category = None

                # Primero buscar/crear categoría por el pos_category
                if pos_categ:
                    category = self.env['product.category'].search([('name', '=', pos_categ.name)], limit=1)
                    if not category:
                        self.env['product.category'].create({
                            'name': pos_categ.name,
                            'parent_id': None,
                        })
                        category = self.env['product.category'].search([('name', '=', pos_categ.name)], limit=1)

                    product_category = self.env['product.category'].search([('name', '=', pos_categ.name)], limit=1)
                    if not product_category:
                        product_category = self.env['product.category'].create({
                            'name': pos_categ.name,
                        })
                else:
                    category = None
                # Si hay proveedor, crear categoría para el proveedor si no existe
                if provider:
                    provider_category_name = f"{provider.name}"
                    provider_category = self.env['product.category'].search([('name', '=', provider_category_name)],
                                                                            limit=1)
                    if not provider_category:
                        provider_category = self.env['product.category'].create({
                            'name': provider_category_name,
                        })

                    # Si existe categoría de producto, hacerla subcategoría del proveedor
                    if product_category:
                        product_category.write({'parent_id': provider_category.id})
                    else:
                        # Si no hay categoría de producto pero sí de proveedor, usamos la de proveedor
                        product_category = provider_category

                if not client:
                    self._register_row_error(errors, excel_row, "cliente no encontrado", row_data=row, client_ref=client_ref)
                    continue

                pricelist_name = f"Tarifa {client.name}"
                pricelist = self.env['product.pricelist'].search([('name', '=', pricelist_name)], limit=1)
                if not pricelist:
                    pricelist = self.env['product.pricelist'].create({'name': pricelist_name, 'company_id': False})
                base_pricelist_name = f"Tarifa {price_line}"
                if product.id == 0 and product_code != '0':
                    _logger.warning("Fila %s: producto no encontrado para referencia %s", excel_row, product_code)
                self._trace_row(
                    excel_row,
                    "resultado de búsquedas",
                    product_id=product.id,
                    product_code=product_code,
                    provider_ref=provider_ref,
                    provider=provider,
                )
                if product.id is False and provider_ref != '0777' and not provider:
                    self._register_row_error(errors, excel_row, "proveedor no encontrado", row_data=row, provider_ref=provider_ref)
                    continue
                if percentage_about_cost != '0':
                    if product.id != 0:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '1_product',
                            'product_tmpl_id': product.id,
                            'base': 'standard_price',
                            'compute_price': 'formula',
                            'price_discount': percentage_about_cost,
                        }
                        if date_start:
                            pricelist_item_vals['date_start'] = date_start
                            pricelist_item_vals['date_end'] = date_end
                        print("Pricelist item vals percentage_about_cost product_id: ", pricelist_item_vals)
                        self._upsert_pricelist_item(
                            errors,
                            excel_row,
                            pricelist_item_vals,
                            search_domain=[('pricelist_id', '=', pricelist.id), ('product_tmpl_id', '=', product.id)],
                            client_ref=client_ref,
                            product_code=product_code,
                            row_data=row,
                        )
                    elif not category:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '3_global',
                            'compute_price': 'formula',
                            'base': 'standard_price',
                            'price_discount': percentage_about_cost,
                        }
                        if date_start:
                            pricelist_item_vals['date_start'] = date_start
                            pricelist_item_vals['date_end'] = date_end
                        if provider:
                            pricelist_item_vals['pricelist_id'] = pricelist.id
                            pricelist_item_vals['applied_on'] = '2_product_category'
                            pricelist_item_vals['display_applied_on'] = '2_product_category'
                            pricelist_item_vals['categ_id'] = product_category.id
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('applied_on', '=', '3_global'),
                        ], limit=1)
                        print("Pricelist item vals percentage_about_cost global: ", pricelist_item_vals)
                        self._upsert_pricelist_item(
                            errors,
                            excel_row,
                            pricelist_item_vals,
                            search_domain=[('pricelist_id', '=', pricelist.id), ('applied_on', '=', '3_global')],
                            client_ref=client_ref,
                            product_code=product_code,
                            row_data=row,
                        )
                    elif size == 0 or size == '':
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '2_product_category',
                            'display_applied_on': '2_product_category',
                            'compute_price': 'formula',
                            'base': 'standard_price',
                            'price_discount': percentage_about_cost,
                            'categ_id': category.id,
                        }
                        if date_start:
                            pricelist_item_vals['date_start'] = date_start
                            pricelist_item_vals['date_end'] = date_end
                        if provider:
                            pricelist_item_vals['pricelist_id'] = pricelist.id
                            pricelist_item_vals['applied_on'] = '2_product_category'
                            pricelist_item_vals['display_applied_on'] = '2_product_category'
                            pricelist_item_vals['categ_id'] = product_category.id
                        else:
                            pricelist_item = self.env['product.pricelist.item'].search([
                                ('pricelist_id', '=', pricelist.id),
                                ('categ_id', '=', category.id),
                            ], limit=1)
                        print("Pricelist item vals percentage_about_cost category: ", pricelist_item_vals)
                        self._upsert_pricelist_item(
                            errors,
                            excel_row,
                            pricelist_item_vals,
                            search_domain=False if provider else [('pricelist_id', '=', pricelist.id), ('categ_id', '=', category.id)],
                            client_ref=client_ref,
                            product_code=product_code,
                            row_data=row,
                        )
                    else:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '2_product_category',
                            'display_applied_on': '2_product_category',
                            'compute_price': 'formula',
                            'base': 'standard_price',
                            'price_discount': percentage_about_cost,
                            'categ_id': category.id,
                            'min_quantity': size,
                        }
                        if date_start:
                            pricelist_item_vals['date_start'] = date_start
                            pricelist_item_vals['date_end'] = date_end
                        if provider:
                            pricelist_item_vals['pricelist_id'] = pricelist.id
                            pricelist_item_vals['applied_on'] = '2_product_category'
                            pricelist_item_vals['display_applied_on'] = '2_product_category'
                            pricelist_item_vals['categ_id'] = product_category.id
                        else:
                            pricelist_item = self.env['product.pricelist.item'].search([
                                ('pricelist_id', '=', pricelist.id),
                                ('categ_id', '=', category.id),
                            ], limit=1)
                        print("Pricelist item vals percentage_about_cost category size: ", pricelist_item_vals)
                        self._upsert_pricelist_item(
                            errors,
                            excel_row,
                            pricelist_item_vals,
                            search_domain=False if provider else [('pricelist_id', '=', pricelist.id), ('categ_id', '=', category.id)],
                            client_ref=client_ref,
                            product_code=product_code,
                            row_data=row,
                        )
                else:
                    if price_line != 0:
                        base_pricelist = self._ensure_base_pricelist(price_line)
                        if not category:
                            if product.id == 0:
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '3_global',
                                    'compute_price': 'formula',
                                    'base': 'pricelist',
                                    'price_discount': discount,
                                    'base_pricelist_id': base_pricelist.id,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                print("Pricelist item vals 1: ", pricelist_item_vals)
                                self._upsert_pricelist_item(
                                    errors,
                                    excel_row,
                                    pricelist_item_vals,
                                    client_ref=client_ref,
                                    product_code=product_code,
                                    row_data=row,
                                )
                            else:
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '1_product',
                                    'product_tmpl_id': product.id,
                                    'compute_price': 'formula',
                                    'base': 'pricelist',
                                    'price_discount': discount,
                                    'base_pricelist_id': base_pricelist.id,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                print("Pricelist item vals 2: ", pricelist_item_vals)
                                self._upsert_pricelist_item(
                                    errors,
                                    excel_row,
                                    pricelist_item_vals,
                                    search_domain=[('pricelist_id', '=', pricelist.id), ('product_tmpl_id', '=', product.id)],
                                    client_ref=client_ref,
                                    product_code=product_code,
                                    row_data=row,
                                )
                        else:
                            if size == 0 or size == '':
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '2_product_category',
                                    'display_applied_on': '2_product_category',
                                    'compute_price': 'formula',
                                    'base': 'pricelist',
                                    'base_pricelist_id': base_pricelist.id,
                                    'categ_id': category.id,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                else:
                                    pricelist_item = self.env['product.pricelist.item'].search([
                                        ('pricelist_id', '=', pricelist.id),
                                        ('categ_id', '=', category.id),
                                    ], limit=1)
                                print("Pricelist item vals 3: ", pricelist_item_vals)
                                self._upsert_pricelist_item(
                                    errors,
                                    excel_row,
                                    pricelist_item_vals,
                                    search_domain=False if provider else [('pricelist_id', '=', pricelist.id), ('categ_id', '=', category.id)],
                                    client_ref=client_ref,
                                    product_code=product_code,
                                    row_data=row,
                                )
                            else:
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '2_product_category',
                                    'display_applied_on': '2_product_category',
                                    'compute_price': 'formula',
                                    'base': 'pricelist',
                                    'base_pricelist_id': base_pricelist.id,
                                    'categ_id': category.id,
                                    'min_quantity': size,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                else:
                                    pricelist_item = self.env['product.pricelist.item'].search([
                                        ('pricelist_id', '=', pricelist.id),
                                        ('categ_id', '=', category.id),
                                    ], limit=1)
                                print("Pricelist item vals 4: ", pricelist_item_vals)
                                self._upsert_pricelist_item(
                                    errors,
                                    excel_row,
                                    pricelist_item_vals,
                                    search_domain=False if provider else [('pricelist_id', '=', pricelist.id), ('categ_id', '=', category.id)],
                                    client_ref=client_ref,
                                    product_code=product_code,
                                    row_data=row,
                                )
                    else:
                        base_pricelist = self._ensure_base_pricelist(price_line)
                        if not category:
                            if fixed_price != '0' and product.id != False:
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '1_product',
                                    'compute_price': 'fixed',
                                    'fixed_price': fixed_price,
                                    'product_tmpl_id': product.id,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                print("Pricelist item vals 5: ", pricelist_item_vals)
                                self._upsert_pricelist_item(
                                    errors,
                                    excel_row,
                                    pricelist_item_vals,
                                    search_domain=[('pricelist_id', '=', pricelist.id), ('product_tmpl_id', '=', product.id)],
                                    client_ref=client_ref,
                                    product_code=product_code,
                                    row_data=row,
                                )
                            else:
                                if product.id == 0:
                                    pricelist_item_vals = {
                                        'pricelist_id': pricelist.id,
                                        'applied_on': '3_global',
                                        'compute_price': 'percentage',
                                        'percent_price': discount,
                                    }
                                    if date_start:
                                        pricelist_item_vals['date_start'] = date_start
                                        pricelist_item_vals['date_end'] = date_end
                                    if provider:
                                        pricelist_item_vals['pricelist_id'] = pricelist.id
                                        pricelist_item_vals['applied_on'] = '2_product_category'
                                        pricelist_item_vals['display_applied_on'] = '2_product_category'
                                        pricelist_item_vals['categ_id'] = product_category.id
                                    print("Pricelist item vals 6: ", pricelist_item_vals)
                                    self._upsert_pricelist_item(
                                        errors,
                                        excel_row,
                                        pricelist_item_vals,
                                        client_ref=client_ref,
                                        product_code=product_code,
                                        row_data=row,
                                    )
                                else:
                                    pricelist_item_vals = {
                                        'pricelist_id': pricelist.id,
                                        'applied_on': '1_product',
                                        'product_tmpl_id': product.id,
                                        'compute_price': 'percentage',
                                        'percent_price': discount,
                                    }
                                    if date_start:
                                        pricelist_item_vals['date_start'] = date_start
                                        pricelist_item_vals['date_end'] = date_end
                                    if product.default_code == '49002015':
                                        print("Pricelist item vals 7: ", pricelist_item_vals)
                                    product = self.env['product.template'].search([('default_code', '=', product_code)], limit=1)
                                    self._upsert_pricelist_item(
                                        errors,
                                        excel_row,
                                        pricelist_item_vals,
                                        search_domain=[('pricelist_id', '=', pricelist.id), ('product_tmpl_id', '=', product.id)],
                                        client_ref=client_ref,
                                        product_code=product_code,
                                        row_data=row,
                                    )
                        else:
                            if size == 0 or size == '':
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '2_product_category',
                                    'display_applied_on': '2_product_category',
                                    'compute_price': 'percentage',
                                    'percent_price': discount,
                                    'categ_id': category.id,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                else:
                                    pricelist_item = self.env['product.pricelist.item'].search([
                                        ('pricelist_id', '=', pricelist.id),
                                        ('categ_id', '=', category.id,),
                                    ], limit=1)
                                print("Pricelist item vals 8: ", pricelist_item_vals)
                                self._upsert_pricelist_item(
                                    errors,
                                    excel_row,
                                    pricelist_item_vals,
                                    search_domain=False if provider else [('pricelist_id', '=', pricelist.id), ('categ_id', '=', category.id)],
                                    client_ref=client_ref,
                                    product_code=product_code,
                                    row_data=row,
                                )
                            else:
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '2_product_category',
                                    'display_applied_on': '2_product_category',
                                    'compute_price': 'percentage',
                                    'percent_price': discount,
                                    'categ_id': category.id,
                                    'min_quantity': size,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                else:
                                    pricelist_item = self.env['product.pricelist.item'].search([
                                        ('pricelist_id', '=', pricelist.id),
                                        ('categ_id', '=', category.id,),
                                    ], limit=1)
                                print("Pricelist item vals 9: ", pricelist_item_vals)
                                self._upsert_pricelist_item(
                                    errors,
                                    excel_row,
                                    pricelist_item_vals,
                                    search_domain=False if provider else [('pricelist_id', '=', pricelist.id), ('categ_id', '=', category.id)],
                                    client_ref=client_ref,
                                    product_code=product_code,
                                    row_data=row,
                                )

                    client.write({'property_product_pricelist': pricelist.id})

            if errors:
                self.error_log = "\n".join(errors)

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'import.client.tariffs.wizard',
                'view_mode': 'form',
                'res_id': self.id,
            }
