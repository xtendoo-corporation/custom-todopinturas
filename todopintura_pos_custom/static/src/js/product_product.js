import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";

patch(ProductProduct.prototype, {
    get_price(pricelist, quantity, price_extra = 0, recurring = false, list_price = false) {
        if (recurring && !pricelist) {
            alert(_t("Un error ocurrió al cargar los precios. Asegúrese de que todas las tarifas estén disponibles en el POS."));
        }

        let price = (list_price || this.lst_price) + (price_extra || 0);
        const rule = this.getPricelistRule(pricelist, quantity);

        if (!rule) {
            return price;
        }

        // Procesamiento de la regla seleccionada
        if (rule.base === "pricelist") {
            if (rule.base_pricelist_id) {
                // Primero comprobar si hay filtro de proveedor
                if (rule.filter_supplier_id) {
                    const hasSupplier = this.seller_ids && this.seller_ids.some(
                        seller => seller.partner_id.id === rule.filter_supplier_id.id
                    );

                    if (!hasSupplier) {
                        console.log(`Regla ignorada: filtro de proveedor ${rule.filter_supplier_id.name} no coincide`);
                        return price; // No aplicar la regla si el proveedor no coincide
                    }

                    console.log(`Aplicando regla con proveedor ${rule.filter_supplier_id.name} basada en tarifa ${rule.base_pricelist_id.name}`);
                }

                // Obtener el precio base de la tarifa referenciada
                price = this.get_price(rule.base_pricelist_id, quantity, 0, true, list_price);
                console.log(`Precio base desde tarifa ${rule.base_pricelist_id.name}: ${price}`);
            }
        } else if (rule.base === "standard_price") {
            price = this.standard_price;
        }

        // Aplicar el cálculo de precio según el tipo de regla
        if (rule.compute_price === "fixed") {
            price = rule.fixed_price;
            console.log(`Aplicando precio fijo: ${price}`);
        } else if (rule.compute_price === "percentage") {
            const oldPrice = price;
            price = price - price * (rule.percent_price / 100);
            console.log(`Aplicando porcentaje ${rule.percent_price}%: ${oldPrice} -> ${price}`);
        } else {
            var price_limit = price;
            const oldPrice = price;
            price -= price * (rule.price_discount / 100);
            console.log(`Aplicando descuento ${rule.price_discount}%: ${oldPrice} -> ${price}`);

            if (rule.price_round) {
                price = roundPrecision(price, rule.price_round);
                console.log(`Redondeando a ${rule.price_round}: ${price}`);
            }
            if (rule.price_surcharge) {
                price += rule.price_surcharge;
                console.log(`Aplicando recargo ${rule.price_surcharge}: ${price}`);
            }
            if (rule.price_min_margin) {
                price = Math.max(price, price_limit + rule.price_min_margin);
                console.log(`Aplicando margen mínimo: ${price}`);
            }
            if (rule.price_max_margin) {
                price = Math.min(price, price_limit + rule.price_max_margin);
                console.log(`Aplicando margen máximo: ${price}`);
            }
        }

        // Registrar información de debug para reglas con proveedor
        if (rule.filter_supplier_id) {
            console.log(`Precio final con regla de proveedor ${rule.filter_supplier_id.name}: ${price}`);
        }

        return price;
    },

    getPricelistRule(pricelist, quantity) {
        const rules = !pricelist ? [] : this.cachedPricelistRules[pricelist?.id] || [];

        if (!rules.length) {
            return undefined;
        }

        // Filtrar reglas por cantidad mínima
        const validRules = rules.filter(rule => !rule.min_quantity || quantity >= rule.min_quantity);

        if (!validRules.length) {
            return undefined;
        }

        // Ordenar reglas según la misma prioridad que en Python
        const prioritizedRules = [...validRules].sort((a, b) => {
            // 1. Producto específico + proveedor (máxima prioridad)
            const aHasProductAndSupplier = (a.product_tmpl_id || a.product_id) && a.filter_supplier_id;
            const bHasProductAndSupplier = (b.product_tmpl_id || b.product_id) && b.filter_supplier_id;

            if (aHasProductAndSupplier && !bHasProductAndSupplier) return -1;
            if (!aHasProductAndSupplier && bHasProductAndSupplier) return 1;

            // 2. Producto específico
            const aHasProduct = a.product_tmpl_id || a.product_id;
            const bHasProduct = b.product_tmpl_id || b.product_id;

            if (aHasProduct && !bHasProduct) return -1;
            if (!aHasProduct && bHasProduct) return 1;

            // 3. Categoría + proveedor
            const aHasCategoryAndSupplier = a.categ_id && a.filter_supplier_id;
            const bHasCategoryAndSupplier = b.categ_id && b.filter_supplier_id;

            if (aHasCategoryAndSupplier && !bHasCategoryAndSupplier) return -1;
            if (!aHasCategoryAndSupplier && bHasCategoryAndSupplier) return 1;

            // 4. Categoría
            const aHasCategory = a.categ_id;
            const bHasCategory = b.categ_id;

            if (aHasCategory && !bHasCategory) return -1;
            if (!aHasCategory && bHasCategory) return 1;

            // 5. Proveedor
            const aHasSupplier = a.filter_supplier_id;
            const bHasSupplier = b.filter_supplier_id;

            if (aHasSupplier && !bHasSupplier) return -1;
            if (!aHasSupplier && bHasSupplier) return 1;

            // 6. Cualquier otra regla
            return 0;
        });

        // Verificar reglas que tienen filtro de proveedor
        for (const rule of prioritizedRules) {
            if (rule.filter_supplier_id) {
                const hasSupplier = this.seller_ids && this.seller_ids.some(
                    seller => seller.partner_id.id === rule.filter_supplier_id.id
                );

                if (!hasSupplier) {
                    continue; // Saltar esta regla si el producto no tiene este proveedor
                }
            }

            return rule;
        }

        // Si llegamos aquí, no hay reglas con filtro de proveedor aplicables,
        // devolver la primera regla válida
        return prioritizedRules[0];
    }
});
