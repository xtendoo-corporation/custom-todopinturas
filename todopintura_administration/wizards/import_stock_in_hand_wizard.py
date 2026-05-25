import base64
import xlrd
import openpyxl
from odoo import api, fields, models
from odoo.exceptions import UserError
from io import BytesIO

class ImportStockWizard(models.TransientModel):
    _name = 'import.stock.in.hand.wizard'
    _description = 'Wizard para importar existencias desde un archivo XLS'

    file = fields.Binary('Subir archivo XLS', required=True)
    file_name = fields.Char('Nombre del archivo')
    error_log = fields.Text('Errores', readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )

    def action_import_stock_in_hand(self):
        if not self.file:
            raise UserError("Por favor, sube un archivo XLS o XLSX.")

        data = base64.b64decode(self.file)
        error_log = []
        processed_count = 0

        # Detectar el tipo de archivo por la extensión
        if self.file_name and self.file_name.lower().endswith('.xlsx'):
            wb = openpyxl.load_workbook(BytesIO(data), data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
        else:
            book = xlrd.open_workbook(file_contents=data)
            sheet = book.sheet_by_index(0)
            rows = [sheet.row_values(row_idx) for row_idx in range(1, sheet.nrows)]

        for row_idx, row in enumerate(rows, start=2):
            try:
                # 1. Obtener identificador del almacén
                raw_wh_val = row[0]
                if raw_wh_val is None or raw_wh_val == '':
                    continue
                try:
                    if isinstance(raw_wh_val, float):
                        ubicacion_num = str(int(raw_wh_val))
                    elif isinstance(raw_wh_val, int):
                        ubicacion_num = str(raw_wh_val)
                    else:
                        ubicacion_num = str(int(float(str(raw_wh_val).strip())))
                except (ValueError, TypeError):
                    ubicacion_num = str(raw_wh_val).strip()

                # Buscar almacén por ID Todopinturas en la compañía seleccionada
                warehouse = self.env['stock.warehouse'].search([
                    ('id_todopinturas', '=', ubicacion_num),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)

                if not warehouse:
                    # Si el almacén existe en otra compañía, se ignora silenciosamente
                    warehouse_any = self.env['stock.warehouse'].search([
                        ('id_todopinturas', '=', ubicacion_num)
                    ], limit=1)
                    if warehouse_any:
                        continue

                    error_log.append(f"Fila {row_idx}: Almacén con ID Todopinturas '{ubicacion_num}' no encontrado.")
                    continue

                location = warehouse.lot_stock_id
                if not location:
                    error_log.append(f"Fila {row_idx}: El almacén '{warehouse.name}' no tiene ubicación de stock configurada.")
                    continue

                # 2. Obtener referencia del producto
                raw_ref_val = row[1]
                if raw_ref_val is None or raw_ref_val == '':
                    continue
                try:
                    if isinstance(raw_ref_val, float) and raw_ref_val.is_integer():
                        ref = str(int(raw_ref_val))
                    else:
                        ref = str(raw_ref_val).strip()
                except Exception:
                    ref = str(raw_ref_val).strip()

                product = self.env['product.product'].search([('default_code', '=', ref)], limit=1)
                if not product:
                    error_log.append(f"Fila {row_idx}: Producto no encontrado: {ref}")
                    continue

                # 3. Obtener cantidad
                qty_value = row[6]
                if isinstance(qty_value, str):
                    qty_value = qty_value.strip()
                    if not qty_value:
                        continue
                try:
                    qty_available = int(float(qty_value))
                except (ValueError, TypeError):
                    continue

                # 4. Actualizar o crear stock.quant
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location.id)
                ], limit=1)

                if quant:
                    quant.quantity = qty_available
                else:
                    self.env['stock.quant'].create({
                        'product_id': product.id,
                        'location_id': location.id,
                        'quantity': qty_available,
                    })
                processed_count += 1
            except Exception as e:
                error_log.append(f"Error en fila {row_idx}: {str(e)}")

        self.error_log = "\n".join(error_log) if error_log else ""

        if self.error_log:
            # Reabrir el asistente para mostrar el log de errores
            return {
                'name': 'Resultado de la Importación',
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Importación finalizada',
                    'message': f'Se han importado las existencias correctamente. Total registros procesados: {processed_count}',
                    'sticky': False,
                },
            }
