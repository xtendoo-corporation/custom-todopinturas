from odoo import models, fields, api
import base64
import xlrd

class ImportCategoriesWizard(models.TransientModel):
    _name = 'import.categories.wizard'
    _description = 'Import Categories Wizard'

    file = fields.Binary(string='File', required=True)
    file_name = fields.Char(string='File Name')

    def action_import_categories(self):
        # Decodificar el archivo XLS
        data = base64.b64decode(self.file)
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)

        category_dict = {}  # Diccionario para mapear las categorías creadas

        for row in range(1, sheet.nrows):
            category_id = int(sheet.cell(row, 0).value)
            category_name = sheet.cell(row, 1).value.strip()

            if not category_name:
                continue

            # Determinar el nivel jerárquico
            parent_id = None  # Por defecto no tiene padre
            if category_id % 10000 == 0:
                parent_id = None  # Es una categoría padre
                print(f"Categoría padre: category_id={category_id}, parent_id={parent_id}")
            elif category_id % 100 == 0:
                parent_id = category_dict.get(category_id - (category_id % 10000))  # Es hija de una categoría padre
                print(f"Hija de categoría padre: category_id={category_id}, parent_id={parent_id}")
            else:
                parent_id = category_dict.get((category_id // 100) * 100)  # Es hija de una hija de una categoría padre
                print(f"Hija de una hija de categoría padre: category_id={category_id}, parent_id={parent_id}")

                # Buscar o crear la categoría
            category = self.env['pos.category'].search([('id', '=', category_id)], limit=1)
            if category:
                category.write({'name': category_name, 'parent_id': parent_id})
                print(f"Categoría actualizada: {category_name}+{category_id}")
            else:
                category = self.env['pos.category'].create({
                    'id': category_id,
                    'name': category_name,
                    'parent_id': parent_id,
                })
                print(f"Categoría creada: {category_name}+{category_id}" )

            # Guardar la categoría en el diccionario
            category_dict[category_id] = category.id

        return {'type': 'ir.actions.client', 'tag': 'reload'}
