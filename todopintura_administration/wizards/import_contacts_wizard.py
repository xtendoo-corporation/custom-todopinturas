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

        payment_terms = {
            '1010': 'GIRO A 30 DIAS',
            '1011': 'GIRO 45 DIAS F.F.',
            '1012': 'GIRO 60 DIAS F.F.',
            '1013': 'GIRO 90 DIAS F.F.',
            '1014': 'GIRO 120 DIAS F.F.',
            '1020': 'GIRO 30-60 DIAS F.F.',
            '1030': 'GIRO 30-60-90 DIAS F.F.',
            '1031': 'GIRO 60-90-120 DIAS F.F.',
            '1040': 'GIRO 30-60-90-120 DIAS F.F.',
            '1041': 'GIRO 60-90-120-150 DIAS F.F.',
            '1021': 'GIRO 60-90 DIAS F.F.',
            '3000': 'CONTADO',
            '4010': 'REPOSICION PAGARE VTO. 30 DIAS FECHA FCT',
            '4020': 'REPOSICION PAGARES VTOS. 30/60 DIAS F.F.',
            '1015': 'GIRO 40 DIAS F.F.',
            '1022': 'GIRO 15-30 DIAS F.F.',
            '2010': 'GIRO PTE. ACEPT. VTO. 30 DIAS F.F.',
            '2011': 'GIRO PTE. ACEPT. VTO. 45 DIAS F.F.',
            '2012': 'GIRO PTE. ACEPT. VTO. 60 DIAS F.F.',
            '2013': 'GIRO PTE. ACEPT. VTO. 90 DIAS F.F.',
            '2014': 'GIRO PTE. ACEPT. VTO. 120 DIAS F.F.',
            '2015': 'GIRO PTE. ACEPT. VTO. 40 DIAS F.F.',
            '2020': 'GIRO PTE. ACEPT. VTO. 30-60 DIAS F.F.',
            '2022': 'GIRO PTE. ACEPT. VTO. 15-30 DIAS F.F.',
            '2030': 'GIRO PTE. ACEPT. VTO. 30-60-90 DIAS F.F.',
            '2031': 'GIRO PTE. ACEPT. VTO. 60-90-120 DIAS F.F',
            '2040': 'GIRO PTE. ACEPT. VTO. 30-60-90-120 DIAS',
            '2041': 'GIRO PTE. ACEPT. VTO. 60-90-120-150 DIAS',
            '2021': 'GIRO PTE. ACEPT. VTO. 60-90 DIAS F.F.',
            '4000': 'REPOSICION',
            '3020': 'CONTRA COMPROMISO',
            '4030': 'REPOSICION PAGARES VTOS. 30/60/90 D. F.F',
            '1016': 'GIRO 10 DIAS F.F.',
            '2032': 'GIRO PTE. ACEPT. VTO. 120-150-180 DIAS',
            '2023': 'GIRO PTE. ACEPT. VTO. 90-120 DIAS F.F.',
            '2033': 'GIRO PTE. ACEPT. VTO. 90-120-150 DIAS',
            '2016': 'GIRO PTE. ACEPT. VTO. 75 DIAS F.F.',
            '2052': 'GIRO PTE. ACEPT. 60-90-120-150-180 DIAS',
            '1033': 'GIRO 90-120-150 DIAS F.F.',
            '2017': 'GIRO PTE. ACEPT. VTO. 180 DIAS F.F.',
            '4040': 'REPOSIC. PAGARES VTOS. 30/60/90/120 F.F.',
            '4011': 'REPOSICION PAGARE VTO. 45 DIAS FECHA FCT',
            '4012': 'REPOSICION PAGARE VTO. 60 DIAS FECHA FCT',
            '4013': 'REPOSICION PAGARE VTO. 85 DIAS FECHA FCT',
            '4014': 'REPOSICION PAGARE VTO. 120 DIAS FECHA F.',
            '4021': 'REPOSICION PAGARES VTOS. 60/90 DIAS F.F.',
            '4022': 'REPOSICION PAGARES VTOS. 15/30 DIAS F.F.',
            '4031': 'REPOSICION PAGARES VTOS. 60/90/120  F.F.',
            '4050': 'TRANSFERENCIA   ES5721009753822200083736',
            '4999': 'CLIENTE OBSOLETO',
            '1017': 'GIRO 150 DIAS F.F.',
            '1023': 'GIRO 90-120 DIAS F.F.',
            '3011': 'RECIBO AL COBRO 15 D. FECHA FCT.VENDEDOR',
            '3012': 'RECIBO AL COBRO 30 D. FECHA FCT.VENDEDOR',
            '4510': 'CONFIRMING 240 DIAS',
            '4501': 'CONFIRMING 60 DIAS',
            '4502': 'CONFIRMING 90 DIAS',
            '4503': 'CONFIRMING 120 DIAS',
            '4504': 'CONFIRMING 180 DIAS',
            '3018': 'REPOSICION TALON BANCARIO 60 DIAS F.F.',
            '3019': 'REPOSICION TALON BANCARIO 90 DIAS F.F.',
            '5000': 'ABONOS AUTOMATICOS',
            '5999': 'FACTURA RECTIFICATIVA ABONO',
            '4505': 'CONFIRMING 150 DIAS',
            '4055': 'TRANSF.365 DIAS ES5721009753822200083736',
            '4015': 'REPOSICION PAGARES VTO. 150 DIAS F.F',
            '1026': 'GIRO 45-90 DIAS F.F.',
            '4041': 'REPOSICION PAGARES VTO: 90/120 F.F.',
            '4506': 'CONFIRMING 45 DIAS',
            '4018': 'REPOSICION PAGARES VTOS.75 DIAS F.F.',
            '1019': 'GIRO 75 DIAS F.F.',
            '3021': 'REPOSICION TALON BANCARIO 75 DIAS F.F',
            '4507': 'CONFIRMING 85 DIAS',
            '1034': 'GIRO 30-60-75 DIAS F.F.',
            '4056': 'TRANSF.15 DIAS ES5721009753822200083736',
            '4019': 'REPOSICION PAGARE VTO. 90 DIAS FECHA FCT',
            '3010': '',
            '3040': '',
            '4057': 'TRANSF.75 DIAS ES5721009753822200083736',
            '4508': 'CONFIRMING 30 60 90',
            '4058': 'TRANSF.85 DIAS ES5721009753822200083736',
            '3500': 'COMPROMISO COMPRAS',
            '4059': 'TRANSF/45 DIAS  ES5721009753822200083736'
        }

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
            forma_pago = str(int(sheet.cell(row, 8).value)) if sheet.cell(row, 8).value else ''
            email = sheet.cell(row, 23).value.strip()
            credit_limit = sheet.cell(row, 11).value
            credit_limit = credit_limit if credit_limit not in [None, 0] else None
            iban = sheet.cell(row, 14).value.strip() if sheet.cell(row, 14).value else None
            observation1 = sheet.cell(row, 19).value
            observation2 = sheet.cell(row, 20).value
            observation3 = sheet.cell(row, 21).value
            observation4 = sheet.cell(row, 22).value

            print(num_client, " ", name, " ", address, " ", cp, " ", telefono, " ", nif, " ", forma_pago, " ", email,
                  " ", credit_limit,
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
            notes = "<br/>".join(filter(None, observations))

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

            if forma_pago in payment_terms:
                print(f"Forma de pago encontrada: {forma_pago} - {payment_terms[forma_pago]}")
                payment_term = self.env['account.payment.term'].search(
                    [('name', '=', payment_terms[forma_pago])], limit=1)
                if payment_term:
                    print(f"Término de pago encontrado: {payment_term.name} (ID: {payment_term.id})")
                    record['property_payment_term_id'] = payment_term.id
                else:
                    print(f"No se encontró un término de pago para: {payment_terms[forma_pago]}")

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
