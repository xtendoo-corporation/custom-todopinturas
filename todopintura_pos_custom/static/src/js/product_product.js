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
            const productSupplierIds = this.seller_ids ? this.seller_ids.map(seller => seller.partner_id.id) : [];

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
            // Procesar reglas de filtro por proveedor ('4_filter_supplier')
            if (rules.supplierItems && rules.supplierItems.length > 0) {
                const supplierRules = rules.supplierItems.filter(rule => {
                    if (rule.filter_supplier_id) {
                        return productSupplierIds.includes(rule.filter_supplier_id.id);
                    }
                    return true;  // Mantener reglas sin filtro específico
                });

                applicableRules[pricelistId].push(...supplierRules);
                if (supplierRules.length && !supplierRules[0].min_quantity) {
                    continue;  // Si hay una regla sin cantidad mínima, detener búsqueda
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

        if (rules.length === 0) {
            return null;
        }

        // Primero, intentamos encontrar reglas con filtro de proveedor
        const supplierRules = rules.filter(rule =>
            rule.applied_on === '4_filter_supplier' &&
            (!rule.min_quantity || quantity >= rule.min_quantity)
        );

        if (supplierRules.length > 0) {
            // Si hay reglas de proveedor aplicables, devolver la primera
            return supplierRules[0];
        }

        // Si no hay reglas de proveedor, aplicar el comportamiento normal
        const applicableRule = rules.find((rule) =>
            !rule.min_quantity || quantity >= rule.min_quantity
        );

        return applicableRule;
    },

    get_price(pricelist, quantity, price_extra = 0, recurring = false, list_price = false, forceSupplierRules = false) {
    if (recurring && !pricelist) {
        alert(
            _t(
                "An error occurred when loading product prices. " +
                    "Make sure all pricelists are available in the POS."
            )
        );
    }

    let price = (list_price || this.lst_price) + (price_extra || 0);
    const rule = this.getPricelistRule(pricelist, quantity);
    if (!rule) {
        return price;
    }

    // Caso especial para reglas con filtro de proveedor
    if (rule.applied_on === '4_filter_supplier' && rule.base === "pricelist") {
        console.log('Calculando precio basado en regla de proveedor:', {
            producto: this.display_name,
            regla: rule.id,
            basePricelist: rule.base_pricelist_id?.id,
            precioLista: this.lst_price
        });
        if (rule.base_pricelist_id) {
            // Obtener el precio de la lista base
            const basePrice = this.get_price(rule.base_pricelist_id, quantity, 0, true, list_price);

            // Aplicar regla al precio base según el tipo de cálculo
            if (rule.compute_price === "fixed") {
                return rule.fixed_price;
            } else if (rule.compute_price === "percentage") {
                return basePrice - basePrice * (rule.percent_price / 100);
            } else {
                let price_limit = basePrice;
                let finalPrice = basePrice - basePrice * (rule.price_discount / 100);

                if (rule.price_round) {
                    finalPrice = roundPrecision(finalPrice, rule.price_round);
                }
                if (rule.price_surcharge) {
                    finalPrice += rule.price_surcharge;
                }
                if (rule.price_min_margin) {
                    finalPrice = Math.max(finalPrice, price_limit + rule.price_min_margin);
                }
                if (rule.price_max_margin) {
                    finalPrice = Math.min(finalPrice, price_limit + rule.price_max_margin);
                }
                return finalPrice;
            }
        }
    }

    // Procesamiento normal para otras reglas
    if (rule.base === "pricelist") {
        if (rule.base_pricelist_id) {
            price = this.get_price(rule.base_pricelist_id, quantity, 0, true, list_price);
        }
    } else if (rule.base === "standard_price") {
        price = this.standard_price;
    }

    if (rule.compute_price === "fixed") {
        price = rule.fixed_price;
    } else if (rule.compute_price === "percentage") {
        price = price - price * (rule.percent_price / 100);
    } else {
        var price_limit = price;
        price -= price * (rule.price_discount / 100);
        if (rule.price_round) {
            price = roundPrecision(price, rule.price_round);
        }
        if (rule.price_surcharge) {
            price += rule.price_surcharge;
        }
        if (rule.price_min_margin) {
            price = Math.max(price, price_limit + rule.price_min_margin);
        }
        if (rule.price_max_margin) {
            price = Math.min(price, price_limit + rule.price_max_margin);
        }
    }

    return price;
}
});
