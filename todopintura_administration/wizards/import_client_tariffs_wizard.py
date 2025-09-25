from odoo import api, fields, models
import base64
import io
try:
    import xlrd
    from xlrd import xldate_as_datetime
except ImportError:
    xlrd = None
try:
    import openpyxl
except ImportError:
    openpyxl = None
from odoo.exceptions import UserError

class ImportClientTariffsWizard(models.TransientModel):
    _name = 'import.client.tariffs.wizard'
    _description = 'Wizard to import client tariffs from an XLS or XLSX file'

    file = fields.Binary('Upload XLS or XLSX file', required=True)
    file_name = fields.Char('File name')
    error_log = fields.Text('Errors', readonly=True)

    def action_import_tariffs(self):
        if not self.file:
            raise UserError("Please upload an XLS or XLSX file.")

        data = base64.b64decode(self.file)
        ext = ''
        if self.file_name:
            ext = self.file_name.split('.')[-1].lower()
        if not ext or ext not in ['xls', 'xlsx']:
            if data[:2] == b'PK':
                ext = 'xlsx'
            elif data[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                ext = 'xls'
        print(f"Extensión detectada: {ext}")
        sheet = None
        is_xlsx = False
        if ext == 'xlsx':
            if not openpyxl:
                raise UserError("Falta la librería openpyxl para procesar archivos .xlsx. Por favor, instálala.")
            is_xlsx = True
            print("Usando openpyxl para .xlsx")
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            sheet = wb.active
        elif ext == 'xls':
            if not xlrd:
                raise UserError("Falta la librería xlrd para procesar archivos .xls. Por favor, instálala.")
            print("Usando xlrd para .xls")
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
        else:
            raise UserError("Formato de archivo no soportado. Usa .xls o .xlsx")

        errors = []
        if is_xlsx:
            print("Procesando filas con openpyxl...")
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
            for row_idx, row in enumerate(rows):
                # Si la fila está vacía, termina la importación
                if not any(row):
                    print(f"Fila vacía detectada en la fila {row_idx+2}. Terminando la importación.")
                    break
                print(f"Fila {row_idx+2} (xlsx): {row}")
                client_ref = str(row[1]).strip()
                provider_ref = f"0{str(row[2]).strip()}" if row[2] else '0'
                product_code = str(row[3]) if row[3] else '0'
                category = row[4]
                category = int(str(category).replace('_', '').strip()) if category and str(category).replace('_', '').strip().isdigit() else 0
                size = str(row[5]).strip() if row[5] else ''
                price_line = int(row[6]) if row[6] else 0
                discount = str(float(row[7])) if row[7] and isinstance(row[7], (int, float)) else '0'
                fixed_price = str(float(row[8])) if row[8] and isinstance(row[8], (int, float)) else '0'
                percentage_about_cost = str(-float(row[9])) if row[9] and isinstance(row[9], (int, float)) else '0'
                client = self.env['res.partner'].search([('ref', '=', client_ref)], limit=1)
                provider = self.env['res.partner'].search([('ref', '=', provider_ref)],
                                                          limit=1) if provider_ref != '0777' else None
                print("*"*50)
                print("Provider ref: ", provider_ref)
                print("Provider: ", provider)
                product = self.env['product.template'].search([('default_code', '=', product_code)], limit=1)
                pos_categ = self.env['pos.category'].search([('referencia_todopintura', '=', category)], limit=1)
                # Procesar fechas
                date_start = row[12]
                date_end = row[13]
                try:
                    if isinstance(date_start, float):
                        date_start = xldate_as_datetime(date_start, book.datemode).strftime('%Y-%m-%d')
                    if isinstance(date_end, float):
                        date_end = xldate_as_datetime(date_end, book.datemode).strftime('%Y-%m-%d')
                    if date_start and date_end and date_end < date_start or date_end == date_start:
                        date_start = None
                        date_end = None
                except Exception:
                    date_start = None
                    date_end = None

                # Gestionar categorías
                product_category = None
                provider_category = None

                # Primero buscar/crear categoría por el pos_category
                if pos_categ:
                    category = self.env['product.category'].search([('name', '=', pos_categ.name)], limit=1)
                    if not category:
                        self.env['product.category'].create({
                            'name': pos_categ.name,
                            'parent_id': None,
                        })
                        category = self.env['product.category'].search([('name', '=', pos_categ.name)], limit=1)

                    product_category = self.env['product.category'].search([('name', '=', pos_categ.name)], limit=1)
                    if not product_category:
                        product_category = self.env['product.category'].create({
                            'name': pos_categ.name,
                        })
                else:
                    category = None
                # Si hay proveedor, crear categoría para el proveedor si no existe
                if provider:
                    provider_category_name = f"{provider.name}"
                    provider_category = self.env['product.category'].search([('name', '=', provider_category_name)],
                                                                            limit=1)
                    if not provider_category:
                        provider_category = self.env['product.category'].create({
                            'name': provider_category_name,
                        })

                    # Si existe categoría de producto, hacerla subcategoría del proveedor
                    if product_category:
                        product_category.write({'parent_id': provider_category.id})
                    else:
                        # Si no hay categoría de producto pero sí de proveedor, usamos la de proveedor
                        product_category = provider_category

                if not client:
                    errors.append(f"Cliente con referencia {client_ref} no encontrado.")
                    continue


                pricelist_name = f"Tarifa {client.name}"
                pricelist = self.env['product.pricelist'].search([('name', '=', pricelist_name)], limit=1)

                base_pricelist_name = f"Tarifa {price_line}"
                if product.id == 0 and product_code != '0':
                    print("Product not found, ref: ", product_code)
                print("*"*50)
                print("Product.id: ", product.id, "Product_code: ", product_code, "Provider_ref: ", provider_ref, "Provider: ", provider)
                if  product.id is False and provider_ref != '0777' and not provider:
                    print("Provider not found, ref: ", provider_ref, ", provider: ", provider)
                    continue
                if percentage_about_cost != '0':
                    if product.id != 0:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '1_product',
                            'product_tmpl_id': product.id,
                            'base': 'standard_price',
                            'compute_price': 'formula',
                            'price_discount': percentage_about_cost,
                        }
                        if date_start:
                            pricelist_item_vals['date_start'] = date_start
                            pricelist_item_vals['date_end'] = date_end
                        print("Pricelist item vals percentage_about_cost product_id: ", pricelist_item_vals)
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('product_tmpl_id', '=', product.id)
                        ], limit=1)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
                    elif not category:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '3_global',
                            'compute_price': 'formula',
                            'base': 'standard_price',
                            'price_discount': percentage_about_cost,
                        }
                        if date_start:
                            pricelist_item_vals['date_start'] = date_start
                            pricelist_item_vals['date_end'] = date_end
                        if provider:
                            pricelist_item_vals['pricelist_id'] = pricelist.id
                            pricelist_item_vals['applied_on'] = '2_product_category'
                            pricelist_item_vals['display_applied_on'] = '2_product_category'
                            pricelist_item_vals['categ_id'] = product_category.id
                        pricelist_item = self.env['product.pricelist.item'].search([
                            ('pricelist_id', '=', pricelist.id),
                            ('applied_on', '=', '3_global'),
                        ], limit=1)
                        print("Pricelist item vals percentage_about_cost global: ", pricelist_item_vals)
                        self.env['product.pricelist.item'].create(pricelist_item_vals)
                    elif size == 0 or size == '':
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '2_product_category',
                            'display_applied_on': '2_product_category',
                            'compute_price': 'formula',
                            'base': 'standard_price',
                            'price_discount': percentage_about_cost,
                            'categ_id': category.id,
                        }
                        if date_start:
                            pricelist_item_vals['date_start'] = date_start
                            pricelist_item_vals['date_end'] = date_end
                        if provider:
                            pricelist_item_vals['pricelist_id'] = pricelist.id
                            pricelist_item_vals['applied_on'] = '2_product_category'
                            pricelist_item_vals['display_applied_on'] = '2_product_category'
                            pricelist_item_vals['categ_id'] = product_category.id
                        else:
                            pricelist_item = self.env['product.pricelist.item'].search([
                                ('pricelist_id', '=', pricelist.id),
                                ('categ_id', '=', category.id),
                            ], limit=1)
                        print("Pricelist item vals percentage_about_cost category: ", pricelist_item_vals)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
                    else:
                        pricelist_item_vals = {
                            'pricelist_id': pricelist.id,
                            'applied_on': '2_product_category',
                            'display_applied_on': '2_product_category',
                            'compute_price': 'formula',
                            'base': 'standard_price',
                            'price_discount': percentage_about_cost,
                            'categ_id': category.id,
                            'min_quantity': size,
                        }
                        if date_start:
                            pricelist_item_vals['date_start'] = date_start
                            pricelist_item_vals['date_end'] = date_end
                        if provider:
                            pricelist_item_vals['pricelist_id'] = pricelist.id
                            pricelist_item_vals['applied_on'] = '2_product_category'
                            pricelist_item_vals['display_applied_on'] = '2_product_category'
                            pricelist_item_vals['categ_id'] = product_category.id
                        else:
                            pricelist_item = self.env['product.pricelist.item'].search([
                                ('pricelist_id', '=', pricelist.id),
                                ('categ_id', '=', category.id),
                            ], limit=1)
                        print("Pricelist item vals percentage_about_cost category size: ", pricelist_item_vals)
                        if pricelist_item:
                            pricelist_item.write(pricelist_item_vals)
                        else:
                            self.env['product.pricelist.item'].create(pricelist_item_vals)
                else:
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
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                print("Pricelist item vals 1: ", pricelist_item_vals)
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
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
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
                                    'display_applied_on': '2_product_category',
                                    'compute_price': 'formula',
                                    'base': 'pricelist',
                                    'base_pricelist_id': base_pricelist.id,
                                    'categ_id': category.id,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                else:
                                    pricelist_item = self.env['product.pricelist.item'].search([
                                        ('pricelist_id', '=', pricelist.id),
                                        ('categ_id', '=', category.id),
                                    ], limit=1)
                                print("Pricelist item vals 3: ", pricelist_item_vals)
                                if pricelist_item:
                                    pricelist_item.write(pricelist_item_vals)
                                else:
                                    self.env['product.pricelist.item'].create(pricelist_item_vals)
                            else:
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '2_product_category',
                                    'display_applied_on': '2_product_category',
                                    'compute_price': 'formula',
                                    'base': 'pricelist',
                                    'base_pricelist_id': base_pricelist.id,
                                    'categ_id': category.id,
                                    'min_quantity': size,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                else:
                                    pricelist_item = self.env['product.pricelist.item'].search([
                                        ('pricelist_id', '=', pricelist.id),
                                        ('categ_id', '=', category.id),
                                    ], limit=1)
                                print("Pricelist item vals 4: ", pricelist_item_vals)
                                if pricelist_item:
                                    pricelist_item.write(pricelist_item_vals)
                                else:
                                    self.env['product.pricelist.item'].create(pricelist_item_vals)
                    else:
                        base_pricelist = self.env['product.pricelist'].search([('name', '=', base_pricelist_name)], limit=1)
                        if not category:
                            if fixed_price != '0' and product.id != False:
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '1_product',
                                    'compute_price': 'fixed',
                                    'fixed_price': fixed_price,
                                    'product_tmpl_id': product.id,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
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
                                    if date_start:
                                        pricelist_item_vals['date_start'] = date_start
                                        pricelist_item_vals['date_end'] = date_end
                                    if provider:
                                        pricelist_item_vals['pricelist_id'] = pricelist.id
                                        pricelist_item_vals['applied_on'] = '2_product_category'
                                        pricelist_item_vals['display_applied_on'] = '2_product_category'
                                        pricelist_item_vals['categ_id'] = product_category.id
                                    print("Pricelist item vals 6: ", pricelist_item_vals)
                                    self.env['product.pricelist.item'].create(pricelist_item_vals)
                                else:
                                    pricelist_item_vals = {
                                        'pricelist_id': pricelist.id,
                                        'applied_on': '1_product',
                                        'product_tmpl_id': product.id,
                                        'compute_price': 'percentage',
                                        'percent_price': discount,
                                    }
                                    if date_start:
                                        pricelist_item_vals['date_start'] = date_start
                                        pricelist_item_vals['date_end'] = date_end
                                    if product.default_code == '49002015':
                                        print("Pricelist item vals 7: ", pricelist_item_vals)
                                    product = self.env['product.template'].search([('default_code', '=', product_code)], limit=1)
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
                                    'display_applied_on': '2_product_category',
                                    'compute_price': 'percentage',
                                    'percent_price': discount,
                                    'categ_id': category.id,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                else:
                                    pricelist_item = self.env['product.pricelist.item'].search([
                                        ('pricelist_id', '=', pricelist.id),
                                        ('categ_id', '=', category.id,),
                                    ], limit=1)
                                print("Pricelist item vals 8: ", pricelist_item_vals)
                                if pricelist_item:
                                    pricelist_item.write(pricelist_item_vals)
                                else:
                                    self.env['product.pricelist.item'].create(pricelist_item_vals)
                            else:
                                pricelist_item_vals = {
                                    'pricelist_id': pricelist.id,
                                    'applied_on': '2_product_category',
                                    'display_applied_on': '2_product_category',
                                    'compute_price': 'percentage',
                                    'percent_price': discount,
                                    'categ_id': category.id,
                                    'min_quantity': size,
                                }
                                if date_start:
                                    pricelist_item_vals['date_start'] = date_start
                                    pricelist_item_vals['date_end'] = date_end
                                if provider:
                                    pricelist_item_vals['pricelist_id'] = pricelist.id
                                    pricelist_item_vals['applied_on'] = '2_product_category'
                                    pricelist_item_vals['display_applied_on'] = '2_product_category'
                                    pricelist_item_vals['categ_id'] = product_category.id
                                else:
                                    pricelist_item = self.env['product.pricelist.item'].search([
                                        ('pricelist_id', '=', pricelist.id),
                                        ('categ_id', '=', category.id,),
                                    ], limit=1)
                                print("Pricelist item vals 9: ", pricelist_item_vals)
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
