from odoo import api, fields, models
import base64
from odoo.exceptions import UserError
import io
try:
    import xlrd
except ImportError:
    xlrd = None
try:
    import openpyxl
except ImportError:
    openpyxl = None


class ImportContactsWizard(models.TransientModel):
    _name = 'import.contacts.wizard'
    _description = 'Wizard para importar contactos desde un archivo XLS o XLSX'

    file = fields.Binary('Subir archivo XLS o XLSX', required=True)
    file_name = fields.Char('Nombre del archivo')

    @api.model
    def _sanitize_import_text(self, value):
        if value is None:
            return ''
        text = value.strip() if isinstance(value, str) else str(value).strip()
        return '' if text and all(char == '*' for char in text) else text

    @api.model
    def _normalize_contact_vat(self, nif):
        nif = self._sanitize_import_text(nif).upper()
        if not nif:
            return '', 'ES'

        nif = ''.join(char for char in nif if char.isalnum())
        country_code = nif[:2] if nif[:2].isalpha() else 'ES'
        vat_number = nif[2:] if nif[:2].isalpha() else nif
        if not vat_number:
            return '', country_code
        return f"{country_code}{vat_number}", country_code

    @api.model
    def _normalize_iban(self, iban):
        iban = self._sanitize_import_text(iban).upper()
        return ''.join(char for char in iban if char.isalnum())

    @api.model
    def _parse_credit_limit(self, value):
        if value in (None, 0, 0.0, False):
            return None
        if isinstance(value, (int, float)):
            return value

        value = self._sanitize_import_text(value)
        if not value:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @api.model
    def _find_existing_contact(self, num_client, name, vat, iban=None):
        partner_model = self.env['res.partner'].with_context(active_test=False)
        base_domain = [('parent_id', '=', False), ('is_company', '=', True)]

        search_domains = []
        if num_client not in ['', None]:
            search_domains.append(base_domain + [('ref', '=', num_client)])
        if vat:
            search_domains.append(base_domain + [('vat', '=', vat)])
        if num_client not in ['', None] and name:
            search_domains.append(base_domain + [('ref', '=', num_client), ('name', '=', name)])
        if vat and name:
            search_domains.append(base_domain + [('vat', '=', vat), ('name', '=', name)])

        for domain in search_domains:
            contact = partner_model.search(domain, limit=1)
            if contact:
                return contact

        normalized_iban = self._normalize_iban(iban)
        if normalized_iban:
            bank_record = self.env['res.partner.bank'].with_context(active_test=False).search([
                ('acc_number', '=', normalized_iban),
            ], limit=1)
            if bank_record:
                return bank_record.partner_id.commercial_partner_id

        return partner_model.browse()

    @api.model
    def _create_or_update_contact(self, num_client, name, record, iban=None):
        contact = self._find_existing_contact(num_client, name, record.get('vat'), iban=iban)

        try:
            if contact:
                write_record = record.copy()
                if contact.company_id and write_record.get('company_id') and contact.company_id.id != write_record['company_id']:
                    write_record.pop('company_id')
                contact.write(write_record)
                print(f"Contacto actualizado: {contact.name}")
            else:
                contact = self.env['res.partner'].create(record)
                print(f"Contacto creado: {name}")
        except Exception as e:
            print(f"Error al actualizar o crear el contacto: {e}")
            fallback_record = record.copy()
            fallback_record['vat'] = ''
            contact = contact or self._find_existing_contact(num_client, name, record.get('vat'), iban=iban)
            if contact:
                if contact.company_id and fallback_record.get('company_id') and contact.company_id.id != fallback_record['company_id']:
                    fallback_record.pop('company_id')
                contact.write(fallback_record)
            else:
                contact = self.env['res.partner'].create(fallback_record)

        return contact

    @api.model
    def _ensure_bank_account(self, contact, iban):
        normalized_iban = self._normalize_iban(iban)
        if not normalized_iban or not contact:
            return

        bank_model = self.env['res.partner.bank'].with_context(active_test=False)
        existing_bank_record = bank_model.search([
            ('acc_number', '=', normalized_iban),
            ('partner_id', '=', contact.id)
        ], limit=1)
        print("Contact ID 2: ", contact.id)
        if not existing_bank_record:
            existing_bank_record = bank_model.search([
                ('acc_number', '=', normalized_iban),
            ], limit=1)

        if not existing_bank_record:
            self.env['res.partner.bank'].create({
                'acc_number': normalized_iban,
                'partner_id': contact.id
            })
            print("Contact ID 3: ", contact.id)
            print(f"Cuenta bancaria creada: {normalized_iban} para {contact.name}")
        else:
            print(
                f"La cuenta bancaria con IBAN: {normalized_iban} ya existe para {existing_bank_record.partner_id.name}. No se crea una nueva.")

    @api.model
    def _prepare_contact_record(self, num_client, name, address, cp, telefono, vat, email, notes, country_id):
        return {
            'ref': num_client,
            'name': name,
            'street': address,
            'zip': cp,
            'country_id': country_id.id,
            'phone': telefono,
            'vat': vat,
            'email': email,
            'comment': notes,
            'is_company': True,
            'company_id': self.env.company.id,
        }

    def action_import_contacts(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS o XLSX.")

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

        ext = ''
        if self.file_name:
            ext = self.file_name.split('.')[-1].lower()
        data = base64.b64decode(self.file)
        if not ext or ext not in ['xls', 'xlsx']:
            if data[:2] == b'PK':
                ext = 'xlsx'
            elif data[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                ext = 'xls'
        sheet = None
        is_xlsx = False
        if ext == 'xlsx':
            if not openpyxl:
                raise UserError("Falta la librería openpyxl para procesar archivos .xlsx. Por favor, instálala.")
            is_xlsx = True
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            sheet = wb.active
        elif ext == 'xls':
            if not xlrd:
                raise UserError("Falta la librería xlrd para procesar archivos .xls. Por favor, instálala.")
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
        else:
            raise UserError("Formato de archivo no soportado. Usa .xls o .xlsx")

        country_id = self.env['res.country'].search([('code', '=', 'ES')], limit=1)
        if not country_id:
            raise UserError("País 'España' no encontrado en la base de datos.")

        if is_xlsx:
            for row in sheet.iter_rows(min_row=2, values_only=True):
                num_client = int(row[0]) if row[0] else ''
                name = self._sanitize_import_text(row[1])
                address = self._sanitize_import_text(row[2])
                cp_value = row[3]
                cp = self._sanitize_import_text(str(int(cp_value)) if cp_value and isinstance(cp_value, (int, float)) else '')
                telefono_value = row[4]
                telefono = self._sanitize_import_text(str(int(telefono_value)) if telefono_value and isinstance(telefono_value, (int, float)) else '')
                nif = self._sanitize_import_text(row[6])
                try:
                    forma_pago = str(int(row[8])) if row[8] else ''
                except (ValueError, TypeError):
                    forma_pago = ''
                email = self._sanitize_import_text(row[23]) if len(row) > 23 else ''
                credit_limit = self._parse_credit_limit(row[11] if len(row) > 11 else None)
                iban = self._sanitize_import_text(row[14]) if len(row) > 14 else ''
                observation1 = str(row[19]).strip() if len(row) > 19 and row[16] is not None else ''
                observation2 = str(row[20]).strip() if len(row) > 20 and row[17] is not None else ''
                observation3 = str(row[21]).strip() if len(row) > 21 and row[18] is not None else ''
                observation4 = str(row[22]).strip() if len(row) > 22 and row[19] is not None else ''

                print(num_client, " ", name, " ", address, " ", cp, " ", telefono, " ", nif, " ", forma_pago, " ",
                      email,
                      " ", credit_limit, " ", iban, " ", observation1, " ", observation2, " ", observation3, " ",
                      observation4)

                if not (name or address or cp or telefono or nif):
                    print("Todos los datos están vacíos. Terminando la importación.")
                    break

                notes = "<br/>".join(filter(None, [observation1, observation2, observation3, observation4]))
                vat, _country_code = self._normalize_contact_vat(nif)
                record = self._prepare_contact_record(num_client, name, address, cp, telefono, vat, email, notes, country_id)

                if credit_limit is not None:
                    record['use_partner_credit_limit'] = True
                    record['credit_limit'] = credit_limit
                    print(f"Límite de crédito establecido: {credit_limit} para {name}")
                if forma_pago in payment_terms:
                    print(f"Forma de pago encontrada: {forma_pago} - {payment_terms[forma_pago]}")
                    payment_term = self.env['account.payment.term'].search(
                        [('name', '=', payment_terms[forma_pago])], limit=1)
                    if payment_term:
                        print(f"Término de pago encontrado: {payment_term.name} (ID: {payment_term.id})")
                        record['property_payment_term_id'] = payment_term.id
                    else:
                        print(f"No se encontró un término de pago para: {payment_terms[forma_pago]}")

                contact = self._create_or_update_contact(num_client, name, record, iban=iban)
                self.env.cr.flush()
                print("Contact ID: ", contact.id)
                self._ensure_bank_account(contact, iban)
        else:
            for row in range(1, sheet.nrows):
                num_client = int(sheet.cell(row, 0).value) if sheet.cell(row, 0).value else ''
                name = self._sanitize_import_text(sheet.cell(row, 1).value)
                address = self._sanitize_import_text(sheet.cell(row, 2).value)
                cp_value = sheet.cell(row, 3).value
                cp = self._sanitize_import_text(str(int(cp_value)) if cp_value and isinstance(cp_value, (int, float)) else '')
                telefono_value = sheet.cell(row, 4).value
                telefono = self._sanitize_import_text(str(int(telefono_value)) if telefono_value and isinstance(telefono_value, (int, float)) else '')
                nif = self._sanitize_import_text(sheet.cell(row, 6).value)
                try:
                    forma_pago = str(int(sheet.cell(row, 8).value)) if sheet.cell(row, 8).value else ''
                except (ValueError, TypeError):
                    forma_pago = ''
                email = self._sanitize_import_text(sheet.cell(row, 23).value)
                credit_limit = self._parse_credit_limit(sheet.cell(row, 11).value)
                iban = self._sanitize_import_text(sheet.cell(row, 14).value)
                observation1 = str(sheet.cell(row, 19).value).strip() if sheet.cell(row, 16).value is not None else ''
                observation2 = str(sheet.cell(row, 20).value).strip() if sheet.cell(row, 17).value is not None else ''
                observation3 = str(sheet.cell(row, 21).value).strip() if sheet.cell(row, 18).value is not None else ''
                observation4 = str(sheet.cell(row, 22).value).strip() if sheet.cell(row, 19).value is not None else ''

                print(num_client, " ", name, " ", address, " ", cp, " ", telefono, " ", nif, " ", forma_pago, " ",
                      email,
                      " ", credit_limit, " ", iban, " ", observation1, " ", observation2, " ", observation3, " ",
                      observation4)

                if not (name or address or cp or telefono or nif):
                    print("Todos los datos están vacíos. Terminando la importación.")
                    break

                notes = "<br/>".join(filter(None, [observation1, observation2, observation3, observation4]))
                vat, _country_code = self._normalize_contact_vat(nif)
                record = self._prepare_contact_record(num_client, name, address, cp, telefono, vat, email, notes, country_id)

                if credit_limit is not None:
                    record['use_partner_credit_limit'] = True
                    record['credit_limit'] = credit_limit
                    print(f"Límite de crédito establecido: {credit_limit} para {name}")
                if forma_pago in payment_terms:
                    print(f"Forma de pago encontrada: {forma_pago} - {payment_terms[forma_pago]}")
                    payment_term = self.env['account.payment.term'].search(
                        [('name', '=', payment_terms[forma_pago])], limit=1)
                    if payment_term:
                        print(f"Término de pago encontrado: {payment_term.name} (ID: {payment_term.id})")
                        record['property_payment_term_id'] = payment_term.id
                    else:
                        print(f"No se encontró un término de pago para: {payment_terms[forma_pago]}")

                contact = self._create_or_update_contact(num_client, name, record, iban=iban)
                self.env.cr.flush()
                print("Contact ID: ", contact.id)
                self._ensure_bank_account(contact, iban)
