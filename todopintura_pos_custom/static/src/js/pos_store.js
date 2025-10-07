/** @odoo-module */
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { CouponAndAssignedPeopleDialog } from "./coupon_and_assigned_people";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { deserializeDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

patch(PosStore.prototype, {
    /**
     * Versión modificada que solo utiliza la lista de precios predeterminada
     */
    computeProductPricelistCache(data) {
        if (data) {
            data = this.data.models[data.model].readMany(data.ids);
        }

        const date = DateTime.now();
        let pricelistItems = this.data.models["product.pricelist.item"].getAll();
        let products = this.data.models["product.product"].getAll();

        // Obtener la lista de precios predeterminada
        const defaultPricelistId = this.config.pricelist_id.id;

        if (data && data.length > 0) {
            if (data[0].model.modelName === "product.product") {
                products = data;
            }

            if (data[0].model.modelName === "product.pricelist.item") {
                // Filtrar solo los elementos de la lista de precios predeterminada
                pricelistItems = data.filter(item => item.pricelist_id.id === defaultPricelistId);

                // Solo computar productos afectados por la lista de precios predeterminada
                const productTmplIds = new Set(pricelistItems.map((item) => item.raw.product_tmpl_id));
                const productIds = new Set(pricelistItems.map((item) => item.raw.product_id));

                if (productTmplIds.size > 0 || productIds.size > 0) {
                    products = products.filter(
                        (product) =>
                            productTmplIds.has(product.raw.product_tmpl_id) ||
                            productIds.has(product.id)
                    );
                }
            }
        } else {
            // Filtrar solo los elementos de la lista de precios predeterminada
            pricelistItems = pricelistItems.filter(item => item.pricelist_id.id === defaultPricelistId);
        }

        const pushItem = (targetArray, key, item) => {
            if (!targetArray[key]) {
                targetArray[key] = [];
            }
            targetArray[key].push(item);
        };

        const pricelistRules = {};
        pricelistRules[defaultPricelistId] = {
            productItems: {},
            productTmlpItems: {},
            categoryItems: {},
            globalItems: [],
        };

        for (const item of pricelistItems) {
            if (
                (item.date_start && deserializeDate(item.date_start, { zone: "utc" }) > date) ||
                (item.date_end && deserializeDate(item.date_end, { zone: "utc" }) < date)
            ) {
                continue;
            }

            // Solo procesar elementos de la lista de precios predeterminada
            if (item.pricelist_id.id !== defaultPricelistId) {
                continue;
            }
            const productId = item.raw.product_id;
            if (productId) {
                pushItem(pricelistRules[defaultPricelistId].productItems, productId, item);
                continue;
            }

            const productTmplId = item.raw.product_tmpl_id;
            if (productTmplId) {
                pushItem(pricelistRules[defaultPricelistId].productTmlpItems, productTmplId, item);
                continue;
            }

            const categId = item.raw.categ_id;
            if (categId) {
                pushItem(pricelistRules[defaultPricelistId].categoryItems, categId, item);
            } else {
                pricelistRules[defaultPricelistId].globalItems.push(item);
            }
        }

        for (const product of products) {
            const applicableRules = product.getApplicablePricelistRules(pricelistRules);

            // Solo procesar reglas para la lista de precios predeterminada
            if (applicableRules[defaultPricelistId]) {
                if (product.cachedPricelistRules[defaultPricelistId]) {
                    const existingRuleIds = product.cachedPricelistRules[defaultPricelistId].map(
                        (rule) => rule.id
                    );
                    const newRules = applicableRules[defaultPricelistId].filter(
                        (rule) => !existingRuleIds.includes(rule.id)
                    );
                    product.cachedPricelistRules[defaultPricelistId] = [
                        ...newRules,
                        ...product.cachedPricelistRules[defaultPricelistId],
                    ];
                } else {
                    product.cachedPricelistRules[defaultPricelistId] = applicableRules[defaultPricelistId];
                }

                // Limpiar cualquier regla de otras listas de precios
                for (const plId in product.cachedPricelistRules) {
                    if (plId != defaultPricelistId) {
                        delete product.cachedPricelistRules[plId];
                    }
                }
            }
        }

        if (data && data.length > 0 && data[0].model.modelName === "product.product") {
            this._loadMissingPricelistItems(products);
        }
    },

    async selectPricelist(pricelist) {
        const oldPricelist = this.getOrder().pricelist_id;

        const data = {
            model: "product.pricelist.item",
            ids: this.data.models["product.pricelist.item"].getAll()
                .filter(item => item.pricelist_id.id === pricelist.id)
                .map(item => item.id)
        };

        await this.computeProductPricelistCacheForSpecificPricelist(data, pricelist);
        await this.getOrder().set_pricelist(pricelist);
    },

    async computeProductPricelistCacheForSpecificPricelist(data, pricelist) {
        const products = this.data.models["product.product"].getAll();
        products.forEach(product => {
            product.prices = {};
        });

        const allPricelists = this.data.models["product.pricelist"].getAll();
        const pricelistItems = this.data.models["product.pricelist.item"].getAll();

        const basePricelistIds = new Set();
        const currentPricelistItems = pricelistItems.filter(item =>
            item.pricelist_id.id === pricelist.id &&
            item.base === 'pricelist' &&
            item.base_pricelist_id
        );

        currentPricelistItems.forEach(item => {
            basePricelistIds.add(item.base_pricelist_id.id);
        });

        for (const basePricelistId of basePricelistIds) {
            const basePricelist = allPricelists.find(pl => pl.id === basePricelistId);
            if (basePricelist) {
                await this.calculatePricesForPricelist(basePricelist, products);
            }
        }

        await this.calculatePricesForPricelist(pricelist, products);

        // Actualizar la UI con doble renderizado
        await new Promise(resolve => {
            if (this.tempScreen?.name === 'ProductScreen') {
                const productScreen = this.tempScreen.component;
                if (productScreen.productListWidget) {
                    productScreen.productListWidget.render();

                    setTimeout(() => {
                        productScreen.productListWidget.render();
                        resolve();
                    }, 100);
                } else {
                    resolve();
                }
            } else {
                this.showScreen('ProductScreen');
                resolve();
            }
        });
    },

    async calculatePricesForPricelist(pricelist, products) {
        const date = DateTime.now();
        const pricelistId = pricelist.id;

        let pricelistItems = this.data.models["product.pricelist.item"].getAll()
            .filter(item => item.pricelist_id.id === pricelistId);

        // Separar las reglas que usan otras listas de precios como base
        const basedOnPricelistItems = pricelistItems.filter(
            item => item.base === 'pricelist' && item.base_pricelist_id
        );

        const pricelistRules = {};
        pricelistRules[pricelistId] = {
            productItems: {},
            productTmlpItems: {},
            categoryItems: {},
            globalItems: [],
        };

        const pushItem = (targetArray, key, item) => {
            if (!targetArray[key]) {
                targetArray[key] = [];
            }
            targetArray[key].push(item);
        };

        for (const item of pricelistItems) {
            if (
                (item.date_start && deserializeDate(item.date_start, { zone: "utc" }) > date) ||
                (item.date_end && deserializeDate(item.date_end, { zone: "utc" }) < date)
            ) {
                continue;
            }

            const productId = item.raw.product_id;
            if (productId) {
                pushItem(pricelistRules[pricelistId].productItems, productId, item);
                continue;
            }

            const productTmplId = item.raw.product_tmpl_id;
            if (productTmplId) {
                pushItem(pricelistRules[pricelistId].productTmlpItems, productTmplId, item);
                continue;
            }

            const categId = item.raw.categ_id;
            if (categId) {
                pushItem(pricelistRules[pricelistId].categoryItems, categId, item);
            } else {
                pricelistRules[pricelistId].globalItems.push(item);
            }
        }

        for (const product of products) {
            delete product.cachedPricelistRules[pricelistId];

            const applicableRules = product.getApplicablePricelistRules(pricelistRules);

            if (applicableRules[pricelistId]) {
                product.cachedPricelistRules[pricelistId] = applicableRules[pricelistId];
                product.get_price(pricelist, 1);
            }
        }
    },

    async selectPartner() {
        const currentOrder = this.getOrder();
        if (!currentOrder) {
            return false;
        }
        const currentPartner = currentOrder.partner_id;
        if (currentPartner && currentOrder.getHasRefundLines()) {
            this.dialog.add(AlertDialog, {
                title: _t("Can't change customer"),
                body: _t(
                    "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer.",
                    currentPartner.name
                ),
            });
            return currentPartner;
        }
        const payload = await makeAwaitable(this.dialog, PartnerList, {
            partner: currentPartner,
            getPayload: (newPartner) => currentOrder.update({ partner_id: newPartner }),
        });

        let newPartner = false;
        if (payload) {
            newPartner = payload.confirmed ? payload.partner_id : currentPartner;

            if (newPartner) {
                const pricelistId = newPartner.property_product_pricelist?.id;
                const pricelist = pricelistId
                    ? this.data.models["product.pricelist"].get(pricelistId)
                    : this.config.pricelist_id;

                if (pricelist) {
                    await this.selectPricelist(pricelist);
                }
            }
        }
        return newPartner;
    },
});
