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
            if len(str(category_id)) == 6:
                # Es una categoría de último nivel (ej. 101001, 101002)
                parent_id = category_dict.get(int(str(category_id)[:5]))  # Padre de 5 dígitos
            elif len(str(category_id)) == 5:
                # Es una subcategoría (ej. 10100, 10200)
                parent_id = category_dict.get(int(str(category_id)[:3] + "00"))  # Padre de 3 dígitos
            elif len(str(category_id)) == 3:
                # Es una categoría principal (ej. 100, 200)
                parent_id = category_dict.get(10000)  # Opcional, depende si 10000 es la raíz global
            elif len(str(category_id)) == 2:
                # Es una categoría raíz (ej. 10, 20)
                parent_id = None

            # Buscar o crear la categoría
            category = self.env['product.category'].search([('id', '=', category_id)], limit=1)
            if category:
                category.write({'name': category_name, 'parent_id': parent_id})
                print(f"Categoría actualizada: {category_name}")
            else:
                category = self.env['product.category'].create({
                    'id': category_id,
                    'name': category_name,
                    'parent_id': parent_id
                })
                print(f"Categoría creada: {category_name}")

            # Guardar la categoría en el diccionario
            category_dict[category_id] = category.id

        return {'type': 'ir.actions.client', 'tag': 'reload'}
