# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from odoo import models, api, fields
from odoo.tools.translate import _
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'barcodes.barcode_events_mixin']


    def on_barcode_scanned(self, barcode):
        print("\n" + "="*80)
        print("TODOPINTURA DEBUG: on_barcode_scanned called")
        print(f"barcode: {barcode}")
        print(f"self: {self}")
        print(f"self.id: {self.id}")
        print("="*80 + "\n")

        _logger.warning("="*80)
        _logger.warning("TODOPINTURA: ON_BARCODE_SCANNED TRIGGERED!")
        _logger.warning(f"Barcode: {barcode}")
        _logger.warning(f"Picking: {self} (ID: {self.id})")
        _logger.warning("="*80)

        # Obtener el picking objetivo (puede ser self o un recordset persistido)
        target = self._get_onchange_target()
        _logger.warning(f"Target picking: {target} (ID: {target.id})")

        _logger.warning("Processing barcode in todopintura_stock_quantity_assign module")
        print("TODOPINTURA: Processing barcode in our custom module")

        # 1. Localizamos el producto
        _logger.warning(f"Step 1: Searching for product with barcode/default_code: {barcode}")
        print(f"TODOPINTURA: Searching for product with barcode: {barcode}")

        product = self.env['product.product'].search(['|', ('barcode', '=', barcode), ('default_code', '=', barcode)], limit=1)

        if not product:
            _logger.warning(f"Product NOT FOUND for barcode: {barcode}")
            print(f"TODOPINTURA: Product NOT FOUND for barcode: {barcode}")
            return {'warning': {
                'title': _('Código no encontrado'),
                'message': _('No se encontró ningún producto con el código de barras %s') % barcode
            }}

        _logger.warning(f"Product FOUND: {product.display_name} (ID: {product.id})")
        print(f"TODOPINTURA: Product FOUND: {product.display_name}")

        # 2. Buscamos el movimiento (línea principal de operación)
        _logger.warning(f"Step 2: Searching for move in picking {target.name}")
        print(f"TODOPINTURA: Searching for move in picking {target.name}")
        print(f"TODOPINTURA: Total moves in picking: {len(target.move_ids)}")

        move = target.move_ids.filtered(lambda m: m.product_id == product and m.state not in ('done', 'cancel'))[:1]

        if not move:
            _logger.warning(f"Move NOT FOUND for product {product.display_name} in picking {target.name}")
            print(f"TODOPINTURA: Move NOT FOUND for product {product.display_name}")
            return {'warning': {
                'title': _('Producto no esperado'),
                'message': _('El producto %s no está en este albarán') % product.display_name
            }}

        _logger.warning(f"Move FOUND: {move.display_name} (ID: {move.id}, state: {move.state})")
        print(f"TODOPINTURA: Move FOUND: {move.display_name}")
        print(f"TODOPINTURA: Move current quantity: {move.quantity}")
        print(f"TODOPINTURA: Move current demand: {move.product_uom_qty}")

        # 3. Buscamos una línea de movimiento existente o la creamos
        # Preferimos líneas sin lot_id, package_id o owner_id para simplificar
        _logger.warning(f"Step 3: Searching for move line")
        print(f"TODOPINTURA: Searching for move line. Total move lines: {len(move.move_line_ids)}")

        line = move.move_line_ids.filtered(
            lambda l: l.state not in ('done', 'cancel') and
                     not l.lot_id and
                     not l.package_id and
                     not l.owner_id
        )[:1]

        if line:
            # Actualizar la línea existente
            old_qty = line.quantity
            new_qty = line.quantity + 1
            _logger.warning(f"Updating existing line {line.id}: {old_qty} -> {new_qty}")
            print(f"TODOPINTURA: Updating existing line: {old_qty} -> {new_qty}")

            line.write({
                'quantity': new_qty,
                'picked': True,
            })
            _logger.warning(f"Line updated successfully. New quantity: {line.quantity}")
            print(f"TODOPINTURA: Line updated. New quantity: {line.quantity}")
        else:
            # Crear nueva línea de movimiento
            _logger.warning(f"Creating NEW move line for product {product.display_name}")
            print(f"TODOPINTURA: Creating NEW move line")

            vals = {
                'move_id': move.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'quantity': 1.0,
                'picking_id': target.id,
                'picked': True,
            }
            print(f"TODOPINTURA: Line values: {vals}")

            line = self.env['stock.move.line'].create(vals)
            _logger.warning(f"New line created successfully. Line ID: {line.id}")
            print(f"TODOPINTURA: New line created. ID: {line.id}")

        # 4. Forzar recalculo del campo quantity del movimiento
        _logger.warning("Step 4: Invalidating cache to force recalculation")
        print("TODOPINTURA: Invalidating cache...")

        move.invalidate_recordset(['quantity', 'picked'])

        _logger.warning(f"SUCCESS! Barcode {barcode} processed for product {product.display_name}")
        _logger.warning(f"Move final quantity: {move.quantity} / {move.product_uom_qty}")
        print(f"TODOPINTURA: SUCCESS! Move final quantity: {move.quantity}")
        print("="*80 + "\n")

        # Devolver información para que el cliente pueda actualizar la UI de forma optimista
        return {
            'updated': True,
            'move_id': move.id,
            'move_line_id': line.id,
            'quantity': float(move.quantity),
        }

    def _get_onchange_target(self):
        """
        Obtiene el picking objetivo para aplicar los cambios.
        Similar a _xt_barcode_get_onchange_target del módulo xtendoo_stock_barcode.
        """
        self.ensure_one()
        if self.id:
            return self
        if self._origin and self._origin.id:
            return self._origin

        params = self.env.context.get("params") or {}
        picking_id = (
            self.env.context.get("active_id")
            or self.env.context.get("id")
            or params.get("id")
            or params.get("resId")
        )
        if picking_id:
            picking = self.env["stock.picking"].browse(picking_id).exists()
            if picking:
                return picking
        return self
