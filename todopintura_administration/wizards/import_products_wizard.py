from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError


class ImportProductsWizard(models.TransientModel):
    _name = 'import.products.wizard'
    _description = 'Wizard para importar productos desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)

    def action_import_products(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS.")

        data = base64.b64decode(self.file)
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)

        errors = []

        tariff_names = [f"Tarifa {i}" for i in range(1, 8)]
        tariffs = {}
        for name in tariff_names:
            tariff = self.env['product.pricelist'].search([('name', '=', name)], limit=1)
            if not tariff:
                tariff = self.env['product.pricelist'].create({'name': name})
            tariffs[name] = tariff

        for row in range(1, sheet.nrows):
            num_prod = int(sheet.cell(row, 0).value)
            try:
                name = str(sheet.cell(row, 1).value).strip()
            except ValueError:
                name = ''
            taxes_id_name = int(sheet.cell(row, 2).value)
            prov_id = '0' + str(int(sheet.cell(row, 17).value))
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

            pos_categ = self.env['pos.category'].search(
                [('referencia_todopintura', '=', int(sheet.cell(row, 28).value))], limit=1).id
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

            if not (num_prod or name or taxes_id_name or barcode or description):
                print("Todos los datos están vacíos. Terminando la importación.")
                break

            tax_id = self.env['account.tax'].search([('name', '=', '21% G')], limit=1).id

            # Extraer precios y descuentos
            precios = []
            descuentos = []
            for i in range(3, 17, 2):
                precio = sheet.cell(row, i).value
                descuento = sheet.cell(row, i + 1).value

                # Convert to string and strip spaces
                precio = str(precio).strip() if precio else ''
                descuento = str(descuento).strip() if descuento else ''

                # Convert to float if valid, else set to None
                precio = float(precio) if precio.replace('.', '', 1).isdigit() else None
                descuento = float(descuento) if descuento.replace('.', '', 1).isdigit() else None

                if precio is not None:
                    precios.append(precio)
                descuentos.append(descuento)

            # Determinar el primer precio disponible
            list_price = next((precio for precio in precios if precio is not None), 0.0)

            record = {
                'default_code': num_prod,
                'name': name,
                'list_price': list_price,
                'taxes_id': [(6, 0, [tax_id])] if tax_id else [],
                'barcode': barcode if barcode else None,
                'description': notes if notes else None,
                'standard_price': coste if coste else 0,
                'invoice_description': invoice_description if invoice_description else None,
                'detailed_type': "product",
                'invoice_policy': "delivery",
                'available_in_pos': True,
                'pos_categ_ids': [(6, 0, [pos_categ])] if pos_categ else [],
            }

            # if prov_id:
            #     provider = self.env['res.partner'].search([('ref', '=', prov_id)], limit=1)
            #     if provider:
            #         prov_name = provider.name
            #         category = self.env['product.category'].search([('name', '=', prov_name)], limit=1)
            #         if not category:
            #             category = self.env['product.category'].create({'name': prov_name})
            #             record['categ_id'] = category.id
            #         else:
            #             record['categ_id'] = category.id
            if pos_categ:
                  #crear una categoria normal igual que este de pos_categ
                    category = self.env['product.category'].search([('name', '=', pos_categ)], limit=1)
                    if not category:
                        category = self.env['product.category'].create({'name': pos_categ})
                        record['categ_id'] = category.id
                    else:
                        record['categ_id'] = category.id
                    product = self._create_or_update_product(record)

                    # Crear o actualizar tarifas
                    for i, tariff_name in enumerate(tariff_names):
                        # Revisa si hay suficientes descuentos disponibles para la tarifa
                        descuento = descuentos[i] if i < len(descuentos) else None

                        # Crea o actualiza la tarifa sólo si hay un descuento disponible
                        if descuento is not None:
                            self.create_or_update_tariffs(product, descuento, tariff_name)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'import.products.wizard',
            'view_mode': 'form',
            'res_id': self.id,
        }

    def _create_or_update_product(self, record):
        if record['name']:
            product = self.env['product.template'].search([('default_code', '=', record['default_code'])], limit=1)
            if product:
                product.write(record)
            else:
                existing_barcode_product = self.env['product.template'].search([('barcode', '=', record['barcode'])], limit=1)
                if existing_barcode_product:
                    record['barcode'] = None
                    print(f"Product with barcode {record['barcode']} already exists. Setting barcode to None.")
                product = self.env['product.template'].create(record)
            return product

    def create_or_update_tariffs(self, product, descuento, tariff_name):
        tariff = self.env['product.pricelist'].search([('name', '=', tariff_name)], limit=1)
        if not tariff:
            tariff = self.env['product.pricelist'].create({'name': tariff_name})

        if descuento is not None and descuento != 0:
            pricelist_item = self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', tariff.id),
                ('product_tmpl_id', '=', product.id)
            ], limit=1)

            pricelist_item_vals = {
                'pricelist_id': tariff.id,
                'product_tmpl_id': product.id,
                'compute_price': 'percentage',
                'percent_price': descuento,
            }

            if pricelist_item:
                print("Producto actualizado")
                pricelist_item.write(pricelist_item_vals)
            else:
                self.env['product.pricelist.item'].create(pricelist_item_vals)
