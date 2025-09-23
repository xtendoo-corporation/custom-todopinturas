from odoo import models, fields, api
import base64
import xlrd
import io
try:
    import openpyxl
except ImportError:
    openpyxl = None

class ImportCategoriesWizard(models.TransientModel):
    _name = 'import.categories.wizard'
    _description = 'Import Categories Wizard'

    file = fields.Binary(string='File', required=True)
    file_name = fields.Char(string='File Name')

    def action_import_categories(self):
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
            if not openpyxl:
                raise Exception("Falta la librería openpyxl para procesar archivos .xlsx. Por favor, instálala.")
            is_xlsx = True
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            sheet = wb.active
        elif ext == 'xls':
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
        else:
            raise Exception("Formato de archivo no soportado. Usa .xls o .xlsx")

        category_dict = {}

        if is_xlsx:
            for row in sheet.iter_rows(min_row=2, values_only=True):
                category_id = int(row[0]) if row[0] else None
                category_name = str(row[1]).strip() if row[1] else ''
                if not category_name:
                    continue
                parent_id = None
                if category_id % 10000 == 0:
                    parent_id = None
                elif category_id % 100 == 0:
                    parent_id = category_dict.get(category_id - (category_id % 10000))
                else:
                    parent_id = category_dict.get((category_id // 100) * 100)
                category = self.env['pos.category'].search([('id', '=', category_id)], limit=1)
                if category:
                    category.write({'name': category_name, 'parent_id': parent_id})
                else:
                    category = self.env['pos.category'].create({
                        'referencia_todopintura': category_id,
                        'name': category_name,
                        'parent_id': parent_id,
                    })
                category_dict[category_id] = category.id
        else:
            for row in range(1, sheet.nrows):
                category_id = int(sheet.cell(row, 0).value)
                category_name = sheet.cell(row, 1).value.strip()
                if not category_name:
                    continue
                parent_id = None
                if category_id % 10000 == 0:
                    parent_id = None
                elif category_id % 100 == 0:
                    parent_id = category_dict.get(category_id - (category_id % 10000))
                else:
                    parent_id = category_dict.get((category_id // 100) * 100)
                category = self.env['pos.category'].search([('id', '=', category_id)], limit=1)
                if category:
                    category.write({'name': category_name, 'parent_id': parent_id})
                else:
                    category = self.env['pos.category'].create({
                        'referencia_todopintura': category_id,
                        'name': category_name,
                        'parent_id': parent_id,
                    })
                category_dict[category_id] = category.id
        return {'type': 'ir.actions.client', 'tag': 'reload'}
