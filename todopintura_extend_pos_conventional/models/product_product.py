# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _pos_barcode_domain(self, barcode):
        """Código de barras exacto sin distinguir mayúsculas/minúsculas.
        '=ilike' sin comodines; se escapan \\ % _ para que valgan literalmente."""
        escaped = barcode.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return Domain("barcode", "=ilike", escaped)

    def _is_pos_line_barcode_only(self):
        """Selector de producto de las líneas del TPV convencional (contexto que
        pone la vista): sin pos_can_manual_product_entry solo se localiza por
        código de barras exacto, nunca por nombre ni listando productos."""
        return bool(
            self.env.context.get("pos_conventional_line_product")
            and not self.env.user.pos_can_manual_product_entry
        )

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        if self._is_pos_line_barcode_only():
            name = (name or "").strip()
            if not name:
                return []
            products = self.search_fetch(
                Domain(domain or Domain.TRUE) & self._pos_barcode_domain(name),
                ["display_name"],
                limit=limit,
            )
            return [(product.id, product.display_name) for product in products.sudo()]
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        # Diálogo "Buscar más...": sin permiso no se puede listar el catálogo
        if self._is_pos_line_barcode_only():
            domain = Domain.FALSE
        return super().web_search_read(
            domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit
        )
