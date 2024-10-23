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
            forma_pago = str(int(sheet.cell(row, 8).value)) if sheet.cell(row, 8).value else ''
            cp_value = sheet.cell(row, 7).value
            cp = str(int(cp_value)) if cp_value and isinstance(cp_value, (int, float)) else ''
            cp = '' if all(char == '*' for char in cp) else cp
            address2 = sheet.cell(row, 9).value.strip()
            address2 = '' if all(char == '*' for char in address2) else address2
            cp2_value = sheet.cell(row, 10).value
            cp2 = str(int(cp2_value)) if cp2_value and isinstance(cp2_value, (int, float)) else ''
            cp2 = '' if all(char == '*' for char in cp2) else cp2
            activo = sheet.cell(row, 15).value
            observation1 = str(sheet.cell(row, 16).value).strip() if sheet.cell(row, 16).value is not None else ''
            observation2 = str(sheet.cell(row, 17).value).strip() if sheet.cell(row, 17).value is not None else ''
            observation3 = str(sheet.cell(row, 18).value).strip() if sheet.cell(row, 18).value is not None else ''
            observation4 = str(sheet.cell(row, 19).value).strip() if sheet.cell(row, 19).value is not None else ''
            observation5 = str(sheet.cell(row, 20).value).strip() if sheet.cell(row, 20).value is not None else ''
            observation6 = str(sheet.cell(row, 21).value).strip() if sheet.cell(row, 21).value is not None else ''
            observation7 = str(sheet.cell(row, 22).value).strip() if sheet.cell(row, 22).value is not None else ''
            observation8 = str(sheet.cell(row, 23).value).strip() if sheet.cell(row, 23).value is not None else ''
            observation9 = str(sheet.cell(row, 24).value).strip() if sheet.cell(row, 24).value is not None else ''
            observation10 = str(sheet.cell(row, 25).value).strip() if sheet.cell(row, 25).value is not None else ''
            observation11 = str(sheet.cell(row, 26).value).strip() if sheet.cell(row, 26).value is not None else ''
            observation12 = str(sheet.cell(row, 27).value).strip() if sheet.cell(row, 27).value is not None else ''
            observation13 = str(sheet.cell(row, 28).value).strip() if sheet.cell(row, 28).value is not None else ''
            observation14 = str(sheet.cell(row, 29).value).strip() if sheet.cell(row, 29).value is not None else ''
            observation15 = str(sheet.cell(row, 30).value).strip() if sheet.cell(row, 30).value is not None else ''
            observation16 = str(sheet.cell(row, 31).value).strip() if sheet.cell(row, 31).value is not None else ''
            observation17 = str(sheet.cell(row, 32).value).strip() if sheet.cell(row, 32).value is not None else ''
            observation18 = str(sheet.cell(row, 33).value).strip() if sheet.cell(row, 33).value is not None else ''
            observation19 = str(sheet.cell(row, 34).value).strip() if sheet.cell(row, 34).value is not None else ''
            observation20 = str(sheet.cell(row, 35).value).strip() if sheet.cell(row, 35).value is not None else ''
            observation21 = str(sheet.cell(row, 36).value).strip() if sheet.cell(row, 36).value is not None else ''
            observation22 = str(sheet.cell(row, 37).value).strip() if sheet.cell(row, 37).value is not None else ''
            observation23 = str(sheet.cell(row, 38).value).strip() if sheet.cell(row, 38).value is not None else ''
            observation24 = str(sheet.cell(row, 39).value).strip() if sheet.cell(row, 39).value is not None else ''

            print("num_prov: " + str(num_prov), "name: " + name, "address: " + address, "telefono: " + telefono,
                  "telefono2: " + telefono2, "nif: " + nif, "cp: " + cp, "address2: " + address2, "cp2: " + cp2,
                  "activo: " + activo)

            observations = [
                observation1,
                observation2,
                observation3,
                observation4,
                observation5,
                observation6,
                observation7,
                observation8,
                observation9,
                observation10,
                observation11,
                observation12,
                observation13,
                observation14,
                observation15,
                observation16,
                observation17,
                observation18,
                observation19,
                observation20,
                observation21,
                observation22,
                observation23,
                observation24
            ]
            notes = "<br/>".join(filter(None, observations))

            if not (name or address or cp or telefono or nif):
                print("Todos los datos están vacíos. Terminando la importación.")
                break

            record = {
                'ref': num_prov,
                'name': name,
                'street': address,
                'zip': cp,
                'country_id': "España",
                'phone': telefono,
                'mobile': telefono2,
                'vat': f"ES{nif}" if nif else '',
                'active': False if activo == 'N' else True,
                'comment': notes,
            }

            if forma_pago in payment_terms:
                print(f"Forma de pago encontrada: {forma_pago} - {payment_terms[forma_pago]}")
                payment_term = self.env['account.payment.term'].search(
                    [('name', '=', payment_terms[forma_pago])], limit=1)
                if payment_term:
                    print(f"Término de pago encontrado: {payment_term.name} (ID: {payment_term.id})")
                    record['property_supplier_payment_term_id'] = payment_term.id
                else:
                    print(f"No se encontró un término de pago para: {payment_terms[forma_pago]}")

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
