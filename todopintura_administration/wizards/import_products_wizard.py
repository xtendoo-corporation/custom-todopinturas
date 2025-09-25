from odoo import api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError
import io
try:
    import openpyxl
except ImportError:
    openpyxl = None


class ImportProductsWizard(models.TransientModel):
    _name = 'import.products.wizard'
    _description = 'Wizard para importar productos desde un archivo XLS o XLSX'

    file = fields.Binary('Subir archivo XLS o XLSX', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)

    def action_import_products(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS o XLSX.")

        data = base64.b64decode(self.file)
        ext = ''
        if self.file_name:
            ext = self.file_name.split('.')[-1].lower()
        # Detección por cabecera si la extensión no es fiable
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
            print("Usando xlrd para .xls")
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
        else:
            raise UserError("Formato de archivo no soportado. Usa .xls o .xlsx")

        errors = []

        tariff_names = [f"Tarifa {i}" for i in range(1, 8)]
        tariffs = {}
        for name in tariff_names:
            tariff = self.env['product.pricelist'].search([('name', '=', name)], limit=1)
            if not tariff:
                tariff = self.env['product.pricelist'].create({'name': name, 'company_id': False})
            tariffs[name] = tariff

        if is_xlsx:
            print("Procesando filas con openpyxl...")
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
            get_cell = lambda row, idx: row[idx] if idx < len(row) else None
            for row_idx, row in enumerate(rows):
                print(f"Fila {row_idx+2} (xlsx): {row}")
                num_prod = int(get_cell(row, 0))
                try:
                    name = str(get_cell(row, 1)).strip()
                except ValueError:
                    name = ''
                taxes_id_name = int(get_cell(row, 2))
                prov_id = '0' + str(int(get_cell(row, 17)))
                barcode_value = get_cell(row, 23)
                if isinstance(barcode_value, float):
                    barcode = str(int(barcode_value)).strip()
                else:
                    barcode = str(barcode_value).strip() if barcode_value else ''
                description = str(get_cell(row, 39)).strip() if get_cell(row, 39) is not None else ''
                try:
                    coste = float(get_cell(row, 24)) if get_cell(row, 24) else 0.0
                except ValueError:
                    coste = 0.0
                art_prov = str(get_cell(row, 22)).strip() if get_cell(row, 22) is not None else ''

                pos_categ = self.env['pos.category'].search(
                    [('referencia_todopintura', '=', int(get_cell(row, 28)))], limit=1)
                print(f"pos_categ: {pos_categ}")
                num_prov = int(get_cell(row, 30)) if get_cell(row, 30) else None
                if num_prov:
                    print(f"Buscando proveedor con referencia: 0{num_prov}")
                    partner = self.env['res.partner'].search([('ref', '=', f'0{num_prov}')], limit=1)
                    if partner:
                        print(f"Proveedor encontrado: {partner.name} (ID: {partner.id})")
                    else:
                        print(f"No se encontró proveedor con referencia 0{num_prov}")
                cell_value = get_cell(row, 24)

                if cell_value and isinstance(cell_value, str):
                    cell_value = cell_value.strip()

                price_last_buy = float(cell_value) if cell_value else None
                observation1 = str(get_cell(row, 40)).strip() if get_cell(row, 40) is not None else ''
                observation2 = str(get_cell(row, 41)).strip() if get_cell(row, 41) is not None else ''
                observation3 = str(get_cell(row, 42)).strip() if get_cell(row, 42) is not None else ''
                observation4 = str(get_cell(row, 43)).strip() if get_cell(row, 43) is not None else ''
                observation5 = str(get_cell(row, 44)).strip() if get_cell(row, 44) is not None else ''
                observation6 = str(get_cell(row, 45)).strip() if get_cell(row, 45) is not None else ''
                observation7 = str(get_cell(row, 46)).strip() if get_cell(row, 46) is not None else ''
                observation8 = str(get_cell(row, 47)).strip() if get_cell(row, 47) is not None else ''
                observation9 = str(get_cell(row, 48)).strip() if get_cell(row, 48) is not None else ''
                invoice_description = str(get_cell(row, 20)).strip() if get_cell(row,
                                                                                   20) is not None else ''

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
                    precio = get_cell(row, i)
                    descuento = get_cell(row, i + 1)

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
                    'type': "consu",
                    'is_storable': True,
                    'invoice_policy': "delivery",
                    'available_in_pos': True,
                    'pos_categ_ids': [(6, 0, [pos_categ])] if pos_categ else [],
                }
                print("*" * 40)
                print(f"Producto: {name} (ID: {num_prod})")
                print("*" * 40)
                partner = None
                if num_prov and price_last_buy:
                    partner = self.env['res.partner'].search([('ref', '=', f'0{num_prov}')], limit=1)

                if pos_categ:
                    record['pos_categ_ids'] = [(6, 0, [pos_categ.id])]
                    category = self.crear_categoria_con_padres(pos_categ, partner)
                    record['categ_id'] = category.id
                    print(f"category: {category}")
                    product = self._create_or_update_product(record)
                    # Create or update product.supplierinfo
                    product_variant = product.product_variant_id
                    if product_variant:
                        if num_prov and price_last_buy:
                            partner = self.env['res.partner'].search([('ref', '=', f'0{num_prov}')], limit=1)
                            if partner:
                                supplierinfo = self.env['product.supplierinfo'].search([
                                    ('product_id', '=', product_variant.id),
                                    ('partner_id', '=', partner.id)
                                ], limit=1)
                                supplierinfo_vals = {
                                    'partner_id': partner.id,
                                    'product_id': product_variant.id,
                                    'price': price_last_buy,
                                }
                                if supplierinfo:
                                    supplierinfo.write(supplierinfo_vals)
                                    print("Proveedor actualizado")
                                else:
                                    self.env['product.supplierinfo'].create(supplierinfo_vals)
                                    print("Proveedor creado")
                    # Crear o actualizar tarifas
                    for i, tariff_name in enumerate(tariff_names):
                        # Revisa si hay suficientes descuentos disponibles para la tarifa
                        descuento = descuentos[i] if i < len(descuentos) else None

                        # Crea o actualiza la tarifa sólo si hay un descuento disponible
                        if descuento is not None:
                            self.create_or_update_tariffs(product, descuento, tariff_name)

                else:
                    if partner:
                        category = self.env['product.category'].search([('name', '=', partner.name)], limit=1)
                        if not category:
                            category = self.env['product.category'].create({'name': partner.name})
                        record['categ_id'] = category.id
                    product = self._create_or_update_product(record)
                    # Create or update product.supplierinfo
                    product_variant = product.product_variant_id
                    if product_variant:
                        if num_prov and price_last_buy:
                            partner = self.env['res.partner'].search([('ref', '=', f'0{num_prov}')], limit=1)
                            if partner:
                                supplierinfo = self.env['product.supplierinfo'].search([
                                    ('product_id', '=', product_variant.id),
                                    ('partner_id', '=', partner.id)
                                ], limit=1)
                                supplierinfo_vals = {
                                    'partner_id': partner.id,
                                    'product_id': product_variant.id,
                                    'price': price_last_buy,
                                }
                                if supplierinfo:
                                    supplierinfo.write(supplierinfo_vals)
                                    print("Proveedor actualizado")
                                else:
                                    self.env['product.supplierinfo'].create(supplierinfo_vals)
                                    print("Proveedor creado")
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
                # Para productos nuevos, usar la categoría calculada
                existing_barcode_product = self.env['product.template'].search([('barcode', '=', record['barcode'])],
                                                                               limit=1)
                if existing_barcode_product and record['barcode']:
                    record['barcode'] = None
                    print(f"Código de barras duplicado. Estableciendo a None.")
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
                'applied_on': '1_product'
            }

            if pricelist_item:
                print("Producto actualizado")
                pricelist_item.write(pricelist_item_vals)
            else:
                self.env['product.pricelist.item'].create(pricelist_item_vals)

    def crear_categoria_con_padres(self, pos_categ, partner=None):
        """
        Crea una estructura de categorías donde:
        1. Si hay proveedor, crea/busca una categoría con su nombre
        2. Crea una subcategoría específica para este proveedor+categoría
        """
        if not partner:
            # Buscar categoría existente por nombre exacto
            category = self.env['product.category'].search([('name', '=', pos_categ.name)], limit=1)
            if not category:
                category = self.env['product.category'].create({'name': pos_categ.name})
                print(f"Categoría creada sin proveedor: {pos_categ.name}")
            else:
                print(f"Usando categoría existente: {pos_categ.name}")
            # Preservar la estructura padre-hijo existente
            parent_pos = pos_categ.parent_id
            if parent_pos and not category.parent_id:
                parent_category = self.crear_categoria_con_padres(parent_pos)
                category.write({'parent_id': parent_category.id})
                print(f"Actualizada jerarquía para: {category.name}")
            return category
        else:
            # Añadir protección adicional para categorías de proveedor
            provider_category = self.env['product.category'].search([('name', '=', partner.name)], limit=1)
            if not provider_category:
                provider_category = self.env['product.category'].create({'name': partner.name})
                print(f"Creada categoría de proveedor: {partner.name}")
            # Búsqueda exacta de subcategoría por nombre y parent_id
            specific_category = self.env['product.category'].search([
                ('name', '=', pos_categ.name),
                ('parent_id', '=', provider_category.id)
            ], limit=1)
            if not specific_category:
                specific_category = self.env['product.category'].create({
                    'name': pos_categ.name,
                    'parent_id': provider_category.id
                })
                print(f"Creada subcategoría: {pos_categ.name} bajo proveedor: {partner.name}")
            else:
                print(f"Usando categoría existente: {pos_categ.name} bajo proveedor: {partner.name}")
            return specific_category
