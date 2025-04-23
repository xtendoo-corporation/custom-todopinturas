from odoo import api, fields, models, _
from odoo.exceptions import UserError

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    def _compute_price_rule(
            self, products, quantity, currency=None, uom=None, date=False, compute_price=True,
            **kwargs
    ):
        self and self.ensure_one()  # self is at most one record

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        # Fetch all rules potentially matching specified products/templates/categories and date
        rules = self._get_applicable_rules(products, date, **kwargs)

        results = {}
        for product in products:
            suitable_rule = self.env['product.pricelist.item']
            product_uom = product.uom_id
            target_uom = uom or product_uom  # If no uom is specified, fall back on the product uom

            # Compute quantity in product uom because pricelist rules are specified
            # w.r.t product default UoM (min_quantity, price_surchage, ...)
            if target_uom != product_uom:
                qty_in_product_uom = target_uom._compute_quantity(
                    quantity, product_uom, raise_if_failure=False
                )
            else:
                qty_in_product_uom = quantity

            # Obtener los IDs de proveedores del producto para comparación eficiente
            product_supplier_ids = product.seller_ids.partner_id.ids

            # Priorizar las reglas según especificidad
            # 1. Producto específico + proveedor específico
            # 2. Producto específico (sin proveedor)
            # 3. Categoría + proveedor específico
            # 4. Categoría (sin proveedor)
            # 5. Solo proveedor específico (4_filter_supplier)
            # 6. Global (3_global)
            prioritized_rules = sorted(rules, key=lambda r: (
                bool(r.product_tmpl_id and r.filter_supplier_id and r.filter_supplier_id.id in product_supplier_ids),
                bool(r.product_tmpl_id and not r.filter_supplier_id),
                bool(r.categ_id and r.filter_supplier_id and r.filter_supplier_id.id in product_supplier_ids),
                bool(r.categ_id and not r.filter_supplier_id),
                bool(
                    r.applied_on == '4_filter_supplier' and r.filter_supplier_id and r.filter_supplier_id.id in product_supplier_ids),
                bool(r.applied_on == '3_global')
            ), reverse=True)

            for rule in prioritized_rules:
                if rule._is_applicable_for(product, qty_in_product_uom):
                    # Si la regla es tipo proveedor pero el proveedor no coincide, saltarla
                    if rule.filter_supplier_id and rule.filter_supplier_id.id not in product_supplier_ids:
                        continue
                    suitable_rule = rule
                    break

            if compute_price:
                price = suitable_rule._compute_price(
                    product, quantity, target_uom, date=date, currency=currency)
            else:
                price = 0.0
            results[product.id] = (price, suitable_rule.id)

        return results
