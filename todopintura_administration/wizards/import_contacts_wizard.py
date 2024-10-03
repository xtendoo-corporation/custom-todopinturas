from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError


class ImportContactsWizard(models.TransientModel):
    _name = 'import.contacts.wizard'
    _description = 'Wizard para importar contactos desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')

    def action_import_contacts(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS.")

        # Decodificar el archivo XLS
        data = base64.b64decode(self.file)
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)

        for row in range(1, sheet.nrows):
            num_client = sheet.cell(row, 0).value
            name = sheet.cell(row, 1).value
            address = sheet.cell(row, 2).value
            cp_value = sheet.cell(row, 3).value
            cp = str(int(cp_value)) if cp_value and isinstance(cp_value, (
                int, float)) else ''
            telefono_value = sheet.cell(row, 4).value
            telefono = str(int(telefono_value)) if telefono_value and isinstance(telefono_value, (
                int, float)) else ''
            nif = sheet.cell(row, 6).value.strip()
            email = sheet.cell(row, 23).value.strip()
            credit_limit = sheet.cell(row, 11).value
            credit_limit = credit_limit if credit_limit not in [None, 0] else None
            iban = sheet.cell(row, 14).value.strip() if sheet.cell(row, 14).value else None
            observation1 = sheet.cell(row, 19).value
            observation2 = sheet.cell(row, 20).value
            observation3 = sheet.cell(row, 21).value
            observation4 = sheet.cell(row, 22).value

            print(num_client, " ", name, " ", address, " ", cp, " ", telefono, " ", nif, " ", email, " ", credit_limit,
                  " ", iban, " ", observation1, " ", observation2, " ", observation3, " ", observation4)

            if not (name or address or cp or telefono or nif):
                print("Todos los datos están vacíos. Terminando la importación.")
                break

            observations = [
                str(observation1) if observation1 else '',
                str(observation2) if observation2 else '',
                str(observation3) if observation3 else '',
                str(observation4) if observation4 else ''
            ]
            notes = "\n".join(filter(None, observations))

            record = {
                'ref': num_client,
                'name': name,
                'street': address,
                'zip': cp,
                'phone': telefono,
                'vat': f"ES{nif}",
                'email': email,
                'comment': notes,
            }

            if credit_limit is not None:
                record['credit_limit'] = credit_limit

            contact = self.env['res.partner'].search([('ref', '=', num_client)], limit=1)

            if contact:
                contact.write(record)
                print(f"Contacto actualizado: {contact.name}")
            else:
                self.env['res.partner'].create(record)
                print(f"Contacto creado: {name}")

            if iban:
                existing_bank_record = self.env['res.partner.bank'].search([
                    ('acc_number', '=', iban),
                    ('partner_id', '=', contact.id)
                ], limit=1)

                if not existing_bank_record:
                    self.env['res.partner.bank'].create({
                        'acc_number': iban,
                        'partner_id': contact.id
                    })
                    print(f"Cuenta bancaria creada: {iban} para {contact.name}")
                else:
                    print(f"La cuenta bancaria con IBAN: {iban} ya existe para {contact.name}. No se crea una nueva.")

