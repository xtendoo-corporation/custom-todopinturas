# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class StockBarcodeInternalWizard(models.TransientModel):
    _inherit = "stock.barcode.internal.wizard"

    def action_continue(self):
        """Al elegir el almacén se cargan las líneas de los productos que ahora mismo
        están bajo mínimos; después se abre la pantalla de transferencias como siempre."""
        self.ensure_one()
        self.env["stock.picking"].tp_load_below_min_lines(self.warehouse_id.id)
        return super().action_continue()
