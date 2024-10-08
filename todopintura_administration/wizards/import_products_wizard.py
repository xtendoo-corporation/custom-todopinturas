from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError


class ImportProductsWizard(models.TransientModel):
    _name = 'import.products.wizard'
    _description = 'Wizard para importar productos desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')

    def action_import_products(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS.")

        # Decodificar el archivo XLS
        data = base64.b64decode(self.file)
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)

        for row in range(1, sheet.nrows):
            num_prod = int(sheet.cell(row, 0).value)
            name = sheet.cell(row, 1).value.strip()
            taxes_id_name = int(sheet.cell(row, 2).value)
            barcode_value = sheet.cell(row, 23).value
            if isinstance(barcode_value, float):
                barcode = str(int(barcode_value)).strip()
            else:
                barcode = str(barcode_value).strip() if barcode_value else ''
            description = str(sheet.cell(row, 39).value).strip() if sheet.cell(row, 39).value is not None else ''
            try:
                coste = float(sheet.cell(row, 24).value) if sheet.cell(row, 24).value else 0.0
            except ValueError:
                coste = 0.0
            art_prov = str(sheet.cell(row, 22).value).strip() if sheet.cell(row, 22).value is not None else ''
            observation1 = str(sheet.cell(row, 40).value).strip() if sheet.cell(row, 40).value is not None else ''
            observation2 = str(sheet.cell(row, 41).value).strip() if sheet.cell(row, 41).value is not None else ''
            observation3 = str(sheet.cell(row, 42).value).strip() if sheet.cell(row, 42).value is not None else ''
            observation4 = str(sheet.cell(row, 43).value).strip() if sheet.cell(row, 43).value is not None else ''
            observation5 = str(sheet.cell(row, 44).value).strip() if sheet.cell(row, 44).value is not None else ''
            observation6 = str(sheet.cell(row, 45).value).strip() if sheet.cell(row, 45).value is not None else ''
            observation7 = str(sheet.cell(row, 46).value).strip() if sheet.cell(row, 46).value is not None else ''
            observation8 = str(sheet.cell(row, 47).value).strip() if sheet.cell(row, 47).value is not None else ''
            observation9 = str(sheet.cell(row, 48).value).strip() if sheet.cell(row, 48).value is not None else ''
            invoice_description = str(sheet.cell(row, 20).value).strip() if sheet.cell(row, 20).value is not None else ''

            observations = [
                description,
                art_prov,
                observation1,
                observation2,
                observation3,
                observation4,
                observation5,
                observation6,
                observation7,
                observation8,
                observation9,
            ]

            notes = "<br/>".join(filter(None, observations))

            print("num_prod: " + str(num_prod), "name: " + name, "taxes_id: " + str(taxes_id_name),
                  "barcode: " + str(barcode),
                  "description: " + description, "coste: " + str(coste))

            if not (num_prod or name or taxes_id_name or barcode or description):
                print("Todos los datos están vacíos. Terminando la importación.")
                break

            tax_id = self.env['account.tax'].search([('name', '=', '21% G')], limit=1).id

            record = {
                'default_code': num_prod,
                'name': name,
                'taxes_id': [(6, 0, [tax_id])] if tax_id else [],
                'barcode': barcode if barcode else None,
                'description': notes if notes else None,
                'standard_price': coste if coste else 0,
                'invoice_description': invoice_description if invoice_description else None
            }

            product = self.env['product.template'].search([('default_code', '=', num_prod)], limit=1)

            if product:
                product.write(record)
                print(f"Producto actualizado: {record['name']}")
            else:
                self.env['product.product'].create(record)
                print(f"Producto creado: {record['name']}")
