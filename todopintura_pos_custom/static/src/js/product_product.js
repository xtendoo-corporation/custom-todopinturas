import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";

patch(ProductProduct.prototype, {
    getApplicablePricelistRules(pricelistRules) {
        const applicableRules = {};
        for (const pricelistId in pricelistRules) {
            applicableRules[pricelistId] = [];
            const rules = pricelistRules[pricelistId];

            // Reglas específicas de producto
            if (rules.productItems[this.id]) {
                // Filtrar reglas por proveedor si es necesario
                const productRules = rules.productItems[this.id].filter(rule => {
                    if (rule.filter_supplier_id) {
                        // Verificar si el producto tiene este proveedor
                        return this.seller_ids && this.seller_ids.some(
                            seller => seller.partner_id.id === rule.filter_supplier_id.id
                        );
                    }
                    return true; // Mantener reglas sin filtro de proveedor
                });

                applicableRules[pricelistId].push(...productRules);
                if (productRules.length && !productRules[0].min_quantity) {
                    continue;
                }
            }

            // Reglas de plantilla de producto
            const productTmplId = this.raw.product_tmpl_id;
            if (rules.productTmlpItems[productTmplId]) {
                // Filtrar reglas por proveedor si es necesario
                const templateRules = rules.productTmlpItems[productTmplId].filter(rule => {
                    if (rule.filter_supplier_id) {
                        return this.seller_ids && this.seller_ids.some(
                            seller => seller.partner_id.id === rule.filter_supplier_id.id
                        );
                    }
                    return true;
                });

                applicableRules[pricelistId].push(...templateRules);
                if (templateRules.length && !templateRules[0].min_quantity) {
                    continue;
                }
            }

            // Reglas por categoría
            for (const category of this.parentCategories) {
                if (rules.categoryItems[category]) {
                    // Filtrar reglas por proveedor si es necesario
                    const categoryRules = rules.categoryItems[category].filter(rule => {
                        if (rule.filter_supplier_id) {
                            return this.seller_ids && this.seller_ids.some(
                                seller => seller.partner_id.id === rule.filter_supplier_id.id
                            );
                        }
                        return true;
                    });

                    applicableRules[pricelistId].push(...categoryRules);
                    if (categoryRules.length && !categoryRules[0].min_quantity) {
                        break;
                    }
                }
            }

            // Reglas globales (también filtradas por proveedor)
            const globalRules = rules.globalItems.filter(rule => {
                if (rule.filter_supplier_id) {
                    return this.seller_ids && this.seller_ids.some(
                        seller => seller.partner_id.id === rule.filter_supplier_id.id
                    );
                }
                return true;
            });

            applicableRules[pricelistId].push(...globalRules);
        }
        return applicableRules;
    },
    getPricelistRule(pricelist, quantity) {
        const rules = !pricelist ? [] : this.cachedPricelistRules[pricelist?.id] || [];
        const applicableRule = rules.find((rule) => !rule.min_quantity || quantity >= rule.min_quantity);
        return applicableRule;
    }
});
