import unicodedata

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _tp_normalize_main_warehouse_name(self, value):
        normalized = unicodedata.normalize("NFKD", value or "")
        return "".join(char for char in normalized if not unicodedata.combining(char)).strip().lower()

    def _tp_has_xtendoo_stock_barcode_access(self):
        self.ensure_one()
        if "property_warehouse_id" not in self._fields:
            return True
        warehouse = self.property_warehouse_id
        if not warehouse:
            return False
        return self._tp_normalize_main_warehouse_name(warehouse.name) == "almacen central"

    def _tp_xtendoo_stock_barcode_visibility_cache_key(self):
        self.ensure_one()
        warehouse = self.property_warehouse_id if "property_warehouse_id" in self._fields else self.env["stock.warehouse"]
        warehouse_name = warehouse.name if warehouse else ""
        warehouse_write_date = fields.Datetime.to_string(warehouse.write_date) if warehouse else False
        return (
            self.id,
            fields.Datetime.to_string(self.write_date) if self.write_date else False,
            warehouse.id if warehouse else False,
            warehouse_write_date,
            self._tp_normalize_main_warehouse_name(warehouse_name),
        )

