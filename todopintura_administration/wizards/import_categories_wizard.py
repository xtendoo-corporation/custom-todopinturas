import base64
import io

from odoo import fields, models
from odoo.exceptions import UserError

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    import openpyxl
except ImportError:
    openpyxl = None


class ImportCategoriesWizard(models.TransientModel):
    _name = 'import.categories.wizard'
    _description = 'Import Categories Wizard'

    file = fields.Binary(string='File', required=True)
    file_name = fields.Char(string='File Name')

    def _safe_category_id(self, value):
        if value in (None, False, ''):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _iter_category_rows(self, sheet, is_xlsx):
        if is_xlsx:
            for row in sheet.iter_rows(min_row=2, values_only=True):
                yield tuple(row)
            return

        for row_idx in range(1, sheet.nrows):
            yield tuple(sheet.row_values(row_idx))

    def _get_parent_reference(self, category_ref):
        if category_ref % 10000 == 0:
            return None
        if category_ref % 100 == 0:
            return category_ref - (category_ref % 10000)
        return (category_ref // 100) * 100

    def _get_category_parent_id(self, category_model, parent_ref, category_refs):
        if not parent_ref:
            return False

        parent_id = category_refs.get(parent_ref)
        if parent_id:
            return parent_id

        parent = category_model.search(
            [('referencia_todopintura', '=', parent_ref)],
            order='id asc',
            limit=1,
        )
        return parent.id or False

    def _create_or_update_category(self, category_model, category_ref, category_name, parent_id):
        category = category_model.search(
            [('referencia_todopintura', '=', category_ref)],
            order='id asc',
            limit=1,
        )

        values = {
            'name': category_name,
            'parent_id': parent_id,
        }
        if category:
            category.write(values)
        else:
            values['referencia_todopintura'] = category_ref
            category = category_model.create(values)

        return category

    def _import_category_rows(self, rows):
        category_models = {
            'pos': self.env['pos.category'],
            'product': self.env['product.category'],
        }
        category_refs = {key: {} for key in category_models}

        for row in rows:
            category_ref = self._safe_category_id(row[0] if len(row) > 0 else None)
            category_name = str(row[1]).strip() if len(row) > 1 and row[1] else ''
            if not category_ref or not category_name:
                continue

            parent_ref = self._get_parent_reference(category_ref)
            for key, category_model in category_models.items():
                parent_id = self._get_category_parent_id(category_model, parent_ref, category_refs[key])
                category = self._create_or_update_category(
                    category_model,
                    category_ref,
                    category_name,
                    parent_id,
                )
                category_refs[key][category_ref] = category.id

    def action_import_categories(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS o XLSX.")

        data = base64.b64decode(self.file)
        ext = ''
        if self.file_name:
            ext = self.file_name.split('.')[-1].lower()
        # Detección por cabecera si la extensión no es fiable
        if not ext or ext not in ['xls', 'xlsx']:
            if data[:2] == b'PK':
                ext = 'xlsx'
            elif data[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                ext = 'xls'
        sheet = None
        is_xlsx = False
        if ext == 'xlsx':
            xlsx_reader = openpyxl
            if not xlsx_reader:
                raise UserError("Falta la librería openpyxl para procesar archivos .xlsx. Por favor, instálala.")
            is_xlsx = True
            wb = xlsx_reader.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            sheet = wb.active
        elif ext == 'xls':
            xls_reader = xlrd
            if not xls_reader:
                raise UserError("Falta la librería xlrd para procesar archivos .xls. Por favor, instálala.")
            book = xls_reader.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
        else:
            raise UserError("Formato de archivo no soportado. Usa .xls o .xlsx")

        self._import_category_rows(self._iter_category_rows(sheet, is_xlsx))
        return {'type': 'ir.actions.client', 'tag': 'reload'}
