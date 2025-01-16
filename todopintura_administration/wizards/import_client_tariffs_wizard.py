from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError

class ImportClientTariffsWizard(models.TransientModel):
    _name = 'import.client.tariffs.wizard'
    _description = 'Wizard to import client tariffs from an XLS file'

    file = fields.Binary('Upload XLS file', required=True)
    file_name = fields.Char('File name')
    error_log = fields.Text('Errors', readonly=True)

    def action_import_tariffs(self):
        if not self.file:
            raise UserError("Please upload an XLS file.")

        data = base64.b64decode(self.file)
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)

        errors = []

        for row in range(1, sheet.nrows):
            client_ref = str(int(sheet.cell(row, 1).value)).strip()
            provider_ref = str(int(sheet.cell(row, 2).value)).strip()
            product_code = str(int(sheet.cell(row, 3).value)).strip()
            price_line = int(sheet.cell(row, 6).value) if sheet.cell(row, 6).value else 0
            discount = sheet.cell(row, 7).value
            discount = str(discount).strip() if discount else ''
            discount = float(discount) if discount.replace('.', '', 1).isdigit() else 0
            print("*"*50)
            print(f"client_ref: {client_ref}, provider_ref: {provider_ref}, product_code: {product_code}, price_line: {price_line}, discount: {discount}")

            client = self.env['res.partner'].search([('ref', '=', client_ref)], limit=1)
            provider = self.env['res.partner'].search([('ref', '=', provider_ref)], limit=1) if provider_ref != '0' else None
            product = self.env['product.product'].search([('default_code', '=', product_code)], limit=1) if product_code != '0' else None

            if not client:
                errors.append(f"Client with reference {client_ref} not found.")
                continue

            pricelist_name = f"Tarifa {client.name}"
            pricelist = self.env['product.pricelist'].search([('name', '=', pricelist_name)], limit=1)
            if not pricelist:
                pricelist = self.env['product.pricelist'].create({'name': pricelist_name})

            base_pricelist_name = f"Tarifa {price_line}"
            base_pricelist = self.env['product.pricelist'].search([('name', '=', base_pricelist_name)], limit=1)
            print(f"base_pricelist_name: {base_pricelist_name}, base_pricelist: {base_pricelist}")
            if not base_pricelist:
                errors.append(f"Base pricelist {base_pricelist_name} not found.")
                continue

            pricelist_item_vals = {
                'pricelist_id': pricelist.id,
                'applied_on': '3_global' if not product else '1_product',
                'product_id': product.id if product else None,
                'compute_price': 'formula',
                'base': 'pricelist',
                'price_discount': discount,
                'base_pricelist_id': base_pricelist.id,
            }

            self.env['product.pricelist.item'].create(pricelist_item_vals)

        if errors:
            self.error_log = "\n".join(errors)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'import.client.tariffs.wizard',
            'view_mode': 'form',
            'res_id': self.id,
        }
