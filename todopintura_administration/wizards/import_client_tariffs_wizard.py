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
            provider_ref = str(int(sheet.cell(row, 2).value)).strip() if sheet.cell(row, 2).value else '0'
            product_code = str(int(sheet.cell(row, 3).value)) if sheet.cell(row, 3).value else '0'
            category = sheet.cell(row, 4).value
            category = int(str(category).replace('_', '').strip()) if category and str(category).replace('_', '').strip().isdigit() else 0
            size = str(int(sheet.cell(row, 5).value)).strip() if sheet.cell(row, 5).value else ''
            price_line = int(sheet.cell(row, 6).value) if sheet.cell(row, 6).value else 0
            discount = str(float(sheet.cell(row, 7).value)) if sheet.cell(row, 7).value and isinstance(sheet.cell(row, 7).value, (int, float)) else '0'
            fixed_price = str(float(sheet.cell(row, 8).value)) if sheet.cell(row, 8).value and isinstance(sheet.cell(row, 8).value, (int, float)) else '0'
            print("*"*50)
            print(category)
            client = self.env['res.partner'].search([('ref', '=', client_ref)], limit=1)
            provider = self.env['res.partner'].search([('ref', '=', provider_ref)], limit=1)
            product = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
            category = self.env['product.category'].search([('id', '=', category)], limit=1)
            print(category)
            if not client:
                errors.append(f"Client with reference {client_ref} not found.")
                continue

            pricelist_name = f"Tarifa {client.name}"
            pricelist = self.env['product.pricelist'].search([('name', '=', pricelist_name)], limit=1)
            if not pricelist:
                pricelist = self.env['product.pricelist'].create({'name': pricelist_name})

            base_pricelist_name = f"Tarifa {price_line}"
            if price_line != 0:
                base_pricelist = self.env['product.pricelist'].search([('name', '=', base_pricelist_name)], limit=1)
                if not category:
                    if product.id == 0:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '3_global',
                            'compute_price': 'formula',
                            'base': 'pricelist',
                            'price_discount': discount,
                            'base_pricelist_id': base_pricelist.id,
                        }
                        print("Pricelist item vals 1: ", pricelist_item_vals)
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('product_tmpl_id', '=', product.id)
                        ], limit=1)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
                    else:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '1_product',
                            'product_tmpl_id': product.id,
                            'compute_price': 'formula',
                            'base': 'pricelist',
                            'price_discount': discount,
                            'base_pricelist_id': base_pricelist.id,
                        }
                        print("Pricelist item vals 2: ", pricelist_item_vals)
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('product_tmpl_id', '=', product.id)
                        ], limit=1)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
                else:
                    if size == 0 or size == '':
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '2_product_category',
                            'compute_price': 'formula',
                            'base': 'pricelist',
                            'base_pricelist_id': base_pricelist.id,
                            'categ_id': category.id,
                        }
                        print("Pricelist item vals 3: ", pricelist_item_vals)
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('product_tmpl_id', '=', product.id)
                        ], limit=1)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
                    else:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '2_product_category',
                            'compute_price': 'formula',
                            'base': 'pricelist',
                            'base_pricelist_id': base_pricelist.id,
                            'categ_id': category.id,
                            'min_quantity': size,
                        }
                        print("Pricelist item vals 4: ", pricelist_item_vals)
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('product_tmpl_id', '=', product.id)
                        ], limit=1)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
            else:
                base_pricelist = self.env['product.pricelist'].search([('name', '=', base_pricelist_name)], limit=1)
                if not category:
                    if fixed_price != '0':
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '1_product',
                            'compute_price': 'fixed',
                            'fixed_price': fixed_price,
                            'product_tmpl_id': product.id,
                        }
                        print("Pricelist item vals 5: ", pricelist_item_vals)
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('product_tmpl_id', '=', product.id)
                        ], limit=1)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
                    else:
                        if product.id == 0:
                            pricelist_item_vals = {
                                'pricelist_id': pricelist.id,
                                'applied_on': '3_global',
                                'compute_price': 'percentage',
                                'percent_price': discount,
                            }
                            print("Pricelist item vals 6: ", pricelist_item_vals)
                            pricelist_item = self.env['product.pricelist.item'].search([
                                ('pricelist_id', '=', pricelist.id),
                                ('product_tmpl_id', '=', product.id)
                            ], limit=1)
                            if pricelist_item:
                                pricelist_item.write(pricelist_item_vals)
                            else:
                                self.env['product.pricelist.item'].create(pricelist_item_vals)
                        else:
                            pricelist_item_vals = {
                                'pricelist_id': pricelist.id,
                                'applied_on': '1_product',
                                'product_tmpl_id': product.id,
                                'compute_price': 'percentage',
                                'percent_price': discount,
                            }
                            print("Pricelist item vals 7: ", pricelist_item_vals)
                            product = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
                            pricelist_item = self.env['product.pricelist.item'].search([
                                ('pricelist_id', '=', pricelist.id),
                                ('product_tmpl_id', '=', product.id)
                            ], limit=1)
                            if pricelist_item:
                                pricelist_item.write(pricelist_item_vals)
                            else:
                                self.env['product.pricelist.item'].create(pricelist_item_vals)
                else:
                    if size == 0 or size == '':
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '2_product_category',
                            'compute_price': 'formula',
                            'base': 'pricelist',
                            'percent_price': discount,
                            'base_pricelist_id': base_pricelist.id,
                            'categ_id': category.id,
                        }
                        print("Pricelist item vals 8: ", pricelist_item_vals)
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('product_tmpl_id', '=', product.id)
                        ], limit=1)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
                    else:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '2_product_category',
                            'compute_price': 'formula',
                            'base': 'pricelist',
                            'percent_price': discount,
                            'base_pricelist_id': base_pricelist.id,
                            'categ_id': category.id,
                            'min_quantity': size,
                        }
                        print("Pricelist item vals 9: ", pricelist_item_vals)
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('product_tmpl_id', '=', product.id)
                        ], limit=1)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)

            client.write({'property_product_pricelist': pricelist.id})

        if errors:
            self.error_log = "\n".join(errors)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'import.client.tariffs.wizard',
            'view_mode': 'form',
            'res_id': self.id,
        }
