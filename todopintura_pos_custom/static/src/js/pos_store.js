/** @odoo-module */
import { Mutex } from "@web/core/utils/concurrency";
import { markRaw } from "@odoo/owl";
import { floatIsZero } from "@web/core/utils/numbers";
import { renderToElement } from "@web/core/utils/render";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { deduceUrl, lte, random5Chars, uuidv4 } from "@point_of_sale/utils";
import { Reactive } from "@web/core/utils/reactive";
import { HWPrinter } from "@point_of_sale/app/printer/hw_printer";
import { ConnectionLostError } from "@web/core/network/rpc";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { _t } from "@web/core/l10n/translation";
import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";
import {
    makeAwaitable,
    ask,
    makeActionAwaitable,
} from "@point_of_sale/app/store/make_awaitable_dialog";
import { deserializeDate } from "@web/core/l10n/dates";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { QRPopup } from "@point_of_sale/app/utils/qr_code_popup/qr_code_popup";
import { ActionScreen } from "@point_of_sale/app/screens/action_screen";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { user } from "@web/core/user";
import { debounce } from "@web/core/utils/timing";
import { openCustomerDisplay } from "@point_of_sale/customer_display/utils";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
const { DateTime } = luxon;
patch(PosStore.prototype, {
    /**
     * Versión modificada que solo utiliza la lista de precios predeterminada
     */
    computeProductPricelistCache(data) {
        console.log("computeProductPricelistCache", data);
        if (data) {
            data = this.models[data.model].readMany(data.ids);
        }

        const date = DateTime.now();
        let pricelistItems = this.models["product.pricelist.item"].getAll();
        let products = this.models["product.product"].getAll();

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
        console.log("selectPricelist method in pos_store.js", pricelist);

        const oldPricelist = this.get_order().pricelist_id;
        console.log("Cambiando de pricelist:", oldPricelist?.name, "a", pricelist.name);

        // Definir el objeto data antes de usarlo
        const data = {
            model: "product.pricelist.item",
            ids: this.models["product.pricelist.item"].getAll()
                .filter(item => item.pricelist_id.id === pricelist.id)
                .map(item => item.id)
        };

        await this.computeProductPricelistCacheForSpecificPricelist(data, pricelist);

        await this.get_order().set_pricelist(pricelist);

        console.log("Pricelist actualizada correctamente a:", this.get_order().pricelist_id?.name);
    },

  async computeProductPricelistCacheForSpecificPricelist(data, pricelist) {
        console.log("computeProductPricelistCacheForSpecificPricelist", data, pricelist.name);
        console.log("Elementos de lista de precios con filter_supplier_id:",
            this.models["product.pricelist.item"].getAll()
            .filter(item => item.filter_supplier_id)
            .map(item => ({
                id: item.id,
                supplier: item.filter_supplier_id,
                pricelist: item.pricelist_id.name
            }))
        );
        // Limpiar cachés agresivamente al inicio para todos los productos
        const products = this.models["product.product"].getAll();
        products.forEach(product => {
            product.prices = {};
        });

        // Encontrar todas las listas de precios que son base para la actual
        const allPricelists = this.models["product.pricelist"].getAll();
        const pricelistItems = this.models["product.pricelist.item"].getAll();

        // Identificar tarifas base necesarias
        const basePricelistIds = new Set();
        const currentPricelistItems = pricelistItems.filter(item =>
            item.pricelist_id.id === pricelist.id &&
            item.base === 'pricelist' &&
            item.base_pricelist_id
        );

        // Recolectar todas las tarifas base
        currentPricelistItems.forEach(item => {
            basePricelistIds.add(item.base_pricelist_id.id);
        });

        console.log(`Tarifas base encontradas: ${basePricelistIds.size}`);

        // Calcular precios para las tarifas base primero
        for (const basePricelistId of basePricelistIds) {
            const basePricelist = allPricelists.find(pl => pl.id === basePricelistId);
            if (basePricelist) {
                console.log(`Calculando precios para tarifa base: ${basePricelist.name}`);
                await this.calculatePricesForPricelist(basePricelist, products);
            }
        }

        // Ahora calcular los precios para la tarifa seleccionada
        console.log(`Calculando precios para tarifa seleccionada: ${pricelist.name}`);
        await this.calculatePricesForPricelist(pricelist, products);

        // Actualizar la UI con doble renderizado
        await new Promise(resolve => {
            if (this.tempScreen?.name === 'ProductScreen') {
                const productScreen = this.tempScreen.component;
                if (productScreen.productListWidget) {
                    productScreen.productListWidget.render();

                    setTimeout(() => {
                        productScreen.productListWidget.render();
                        console.log("UI actualizada con doble renderizado");
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

        console.log(`Caché de precios completada para pricelist: ${pricelist.name}`);
    },

    // Nuevo método para calcular precios específicos de una tarifa
    async calculatePricesForPricelist(pricelist, products) {
        const date = DateTime.now();
        const pricelistId = pricelist.id;

        let pricelistItems = this.models["product.pricelist.item"].getAll()
            .filter(item => item.pricelist_id.id === pricelistId);

        const pricelistRules = {};
        pricelistRules[pricelistId] = {
            productItems: {},
            productTmlpItems: {},
            categoryItems: {},
            globalItems: [],
        };

        // Función auxiliar para agregar elementos
        const pushItem = (targetArray, key, item) => {
            if (!targetArray[key]) {
                targetArray[key] = [];
            }
            targetArray[key].push(item);
        };

        // Clasificar los items por tipo
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

        // Calcular precios para cada producto
        for (const product of products) {
            // Limpiar reglas existentes para esta lista de precios
            delete product.cachedPricelistRules[pricelistId];

            // Calcular nuevas reglas aplicables
            const applicableRules = product.getApplicablePricelistRules(pricelistRules);

            if (applicableRules[pricelistId]) {
                product.cachedPricelistRules[pricelistId] = applicableRules[pricelistId];

                // Forzar cálculo explícito del precio con la nueva tarifa
                product.get_price(pricelist, 1);
            }
        }
    },

    async selectPartner() {
        const currentOrder = this.get_order();
        if (!currentOrder) {
            return false;
        }
        const currentPartner = currentOrder.get_partner();
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
            getPayload: (newPartner) => currentOrder.set_partner(newPartner),
        });

        let newPartner = false;
        if (payload) {
            currentOrder.set_partner(payload);
            newPartner = payload;
        } else {
            currentOrder.set_partner(false);
        }

        // Si el cliente tiene una tarifa específica, aplicarla
        if (newPartner) {
            console.log("Cliente seleccionado:", newPartner.name);

            // Obtener tarifa usando el mismo método que updatePricelistAndFiscalPosition
            const customerPricelist = this.models["product.pricelist"].find(
                (pricelist) => pricelist.id === newPartner.property_product_pricelist?.id
            );

            console.log("Tarifa del cliente encontrada:", customerPricelist?.name);

            // Limpiar cachés de productos
            const products = this.models["product.product"].getAll();
            products.forEach(product => {
                product.prices = {};
                product.cachedPricelistRules = {};
            });

            // Usar selectPricelist para actualizar la tarifa
            await this.selectPricelist(customerPricelist);

            // Forzar actualización de la UI
            setTimeout(() => {
                if (this.tempScreen?.name === 'ProductScreen') {
                    const productScreen = this.tempScreen.component;
                    if (productScreen.productListWidget) {
                        productScreen.productListWidget.render();
                    }
                }
            }, 200);
        }
        return currentPartner;
    },
    async ready() {
        const result = await this._super(...arguments);

        // Cargar todos los contactos una sola vez al inicio
        const allPartners = this.models["res.partner"].getAll();
        console.log(`Cargados ${allPartners.length} contactos al inicio`);

        // Si no hay suficientes contactos, intentar cargarlos todos
        if (allPartners.length < 1000) {
            console.log("Cargando todos los contactos disponibles...");
            try {
                await this.data.loadPartnersBackground();
                const partnersAfterLoad = this.models["res.partner"].getAll();
                console.log(`Contactos cargados después de forzar: ${partnersAfterLoad.length}`);
            } catch (error) {
                console.error("Error al cargar contactos:", error);
            }
        }

        return result;
    },
});
