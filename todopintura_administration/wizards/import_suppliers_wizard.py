from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError


class ImportSuppliersWizard(models.TransientModel):
    _name = 'import.suppliers.wizard'
    _description = 'Wizard para importar proveedores desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')

    def action_import_suppliers(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS.")

        # Decodificar el archivo XLS
        data = base64.b64decode(self.file)
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)

        for row in range(1, sheet.nrows):
            num_prov = sheet.cell(row, 0).value
            name = sheet.cell(row, 1).value.strip()
            address = sheet.cell(row, 2).value.strip()
            address = '' if all(char == '*' for char in address) else address
            telefono_value = sheet.cell(row, 3).value
            telefono = str(int(telefono_value)) if telefono_value and isinstance(telefono_value, (int, float)) else ''
            telefono = '' if all(char == '*' for char in telefono) else telefono
            telefono2_value = sheet.cell(row, 4).value
            telefono2 = str(int(telefono2_value)) if telefono2_value and isinstance(telefono2_value,
                                                                                    (int, float)) else ''
            telefono2 = '' if all(char == '*' for char in telefono2) else telefono2
            nif = sheet.cell(row, 5).value.strip()
            nif = '' if all(char == '*' for char in nif) else nif
            cp_value = sheet.cell(row, 7).value
            cp = str(int(cp_value)) if cp_value and isinstance(cp_value, (int, float)) else ''
            cp = '' if all(char == '*' for char in cp) else cp
            address2 = sheet.cell(row, 9).value.strip()
            address2 = '' if all(char == '*' for char in address2) else address2
            cp2_value = sheet.cell(row, 10).value
            cp2 = str(int(cp2_value)) if cp2_value and isinstance(cp2_value, (int, float)) else ''
            cp2 = '' if all(char == '*' for char in cp2) else cp2


            print("num_prov: " + str(num_prov), "name: " + name, "address: " + address, "telefono: " + telefono,
                  "telefono2: " + telefono2, "nif: " + nif, "cp: " + cp, "address2: " + address2, "cp2: " + cp2)

            if not (name or address or cp or telefono or nif):
                print("Todos los datos están vacíos. Terminando la importación.")
                break

            record = {
                'ref': num_prov,
                'name': name,
                'street': address,
                'zip': cp,
                'phone': telefono,
                'mobile': telefono2,
                'vat': f"ES{nif}" if nif else '',
            }

            supplier = self.env['res.partner'].search(['|', ('ref', '=', num_prov), ('name', '=', name)], limit=1)

            if supplier:
                supplier.write(record)
                print(f"Proveedor actualizado: {supplier.name}")

            else:
                self.env['res.partner'].create(record)
                print(f"Proveedor creado: {name}")

            if address2 or cp2:
                contact_address = {
                    'name': "Otra dirección",
                    'parent_id': supplier.id,
                    'type': 'other',
                    'street': address2,
                    'zip': cp2,
                }
                existing_contact = self.env['res.partner'].search([
                    ('name', '=', "Otra dirección"),
                    ('parent_id', '=', supplier.id),
                    ('type', '=', 'other'),
                    ('street', '=', address2),
                    ('zip', '=', cp2)
                ], limit=1)

                if existing_contact:
                    existing_contact.write(contact_address)
                    print(f"Dirección secundaria actualizada: {address2}")
                else:
                    self.env['res.partner'].create(contact_address)
                    print(f"Dirección secundaria creada: {address2}")
