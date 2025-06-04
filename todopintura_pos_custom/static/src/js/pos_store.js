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
import { CouponAndAssignedPeopleDialog } from "./coupon_and_assigned_people";
import { browser } from "@web/core/browser/browser";
const { DateTime } = luxon;
const originalProcessServerData = PosStore.prototype.processServerData;
const originalSetup = PosStore.prototype.setup;
patch(PosStore.prototype, {
    /**
     * Versión modificada que solo utiliza la lista de precios predeterminada
     */
    computeProductPricelistCache(data) {
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

        const oldPricelist = this.get_order().pricelist_id;

        // Definir el objeto data antes de usarlo
        const data = {
            model: "product.pricelist.item",
            ids: this.models["product.pricelist.item"].getAll()
                .filter(item => item.pricelist_id.id === pricelist.id)
                .map(item => item.id)
        };

        await this.computeProductPricelistCacheForSpecificPricelist(data, pricelist);

        await this.get_order().set_pricelist(pricelist);

    },

  async computeProductPricelistCacheForSpecificPricelist(data, pricelist) {
        const products = this.models["product.product"].getAll();
        products.forEach(product => {
            product.prices = {};
        });

        const allPricelists = this.models["product.pricelist"].getAll();
        const pricelistItems = this.models["product.pricelist.item"].getAll();

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

        let pricelistItems = this.models["product.pricelist.item"].getAll()
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
            // Verificar si hay reglas basadas en otra tarifa + filtro proveedor

            product.cachedPricelistRules[pricelistId] = applicableRules[pricelistId];

            // Calcular el precio considerando reglas basadas en otras tarifas
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
        // Verificar si el cliente tiene personas asignadas
        console.log("Payload:", payload);
        const tienePersonasAsignadas = payload.assigned_persons_info;
        console.log("Tiene personas asignadas:", tienePersonasAsignadas);
        console.log("Campo voucher:", payload.voucher);
        console.log("Campo assigned_persons:", payload.assigned_persons);
        console.log("Campo credit_sale:", payload.credit_sale);
        console.log("Nombre de ubicación:", payload.credit_location_id_name);
        if (payload.credit_sale) {
            console.log("Cliente con venta a crédito", payload.credit_location_id_name);

            try {
                const result = await this.env.services.orm.call(
                    'res.partner',
                    'check_credit_location_matches_pos',
                    [[payload.id], this.config.id]
                );

                console.log("Resultado verificación de ubicación:", result);

                // Guardar la información de coincidencia en el objeto cliente
                payload.credit_location_mismatch = !result.matches;

                if (!result.matches) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Ubicación incorrecta para realizar venta a crédito"),
                        body: _t("La ubicación de crédito del cliente (" + result.partner_location_name +
                              ") no coincide con la ubicación de esta caja (" + result.pos_location_name + "). En esta tienda no se puede realizar venta a crédito a este cliente."),
                    });
                }
            } catch (error) {
                console.error("Error al verificar ubicación:", error);
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("No se pudo verificar la ubicación de crédito."),
                });
            }
        }
    if (tienePersonasAsignadas) {
        try {
            // Verificamos qué servicios están disponibles
            console.log("this.dialog:", this.dialog);
            console.log("this.env:", this.env);
            console.log("this.env?.services:", this.env?.services);

            const option = await new Promise(resolve => {
                this.dialog.add(CouponAndAssignedPeopleDialog, {
                    partner: payload,
                    assignedPeopleInfo: tienePersonasAsignadas, // Pasamos la información de personas asignadas
                    confirm: resolve,
                    close: () => resolve(false)
                });
            });
        } catch (error) {
            console.error("Error al mostrar el diálogo:", error);
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("No se pudo mostrar el diálogo: ") + (error.message || error),
            });
        }
    }

        newPartner = payload;
        currentOrder.set_partner(newPartner);
    } else {
        currentOrder.set_partner(false);
    }

     if (newPartner) {
    const customerPricelist = this.models["product.pricelist"].find(
        (pricelist) => pricelist.id === newPartner.property_product_pricelist?.id
    );

    const products = this.models["product.product"].getAll();
    products.forEach(product => {
        product.prices = {};
        product.cachedPricelistRules = {};
    });

    await this.selectPricelist(customerPricelist);

    // Solo recalcular si hay líneas en el pedido
    if (currentOrder.get_orderlines().length > 0) {
        // Recalcular precio para cada línea existente
        for (const orderline of currentOrder.get_orderlines()) {
            const product = orderline.get_product();

            // Guardar si el precio y descuento fueron establecidos manualmente
            const priceManuallySet = orderline.price_manually_set;
            const discountManuallySet = orderline.discount_manually_set;

            // Obtener precio base (sin descuentos)
            const precioBase = product.lst_price || product.list_price || 0;

            // Obtener precio calculado con la nueva tarifa
            const precioCalculado = product.get_price(currentOrder.pricelist_id, orderline.get_quantity());

            let precioReal = precioCalculado;

            // Buscar reglas específicas de tarifa para este producto
            try {
                if (customerPricelist && customerPricelist.items) {
                    const tarifaItem = customerPricelist.items.find(item =>
                        item.product_id && item.product_id[0] === product.id);

                    if (tarifaItem && tarifaItem.fixed_price) {
                        precioReal = tarifaItem.fixed_price;
                    } else if (tarifaItem && tarifaItem.percent_price) {
                        precioReal = precioBase * (1 - tarifaItem.percent_price / 100);
                    }
                }
            } catch (error) {
                console.log("Error al buscar regla de tarifa:", error);
            }

            // Usar el precio más bajo entre calculado y real
            const usarPrecio = Math.min(precioCalculado, precioReal);

            // Si hay diferencia entre precio base y calculado, aplicar descuento visual
            if (precioBase > usarPrecio && Math.abs(precioBase - usarPrecio) > 0.0001) {
                // Calcular porcentaje de descuento
                const porcentajeDescuento = Math.round((1 - (usarPrecio / precioBase)) * 100 * 100) / 100;

                // Solo modificar si no fueron establecidos manualmente
                if (!priceManuallySet) {
                    orderline.set_unit_price(precioBase);
                }

                if (!discountManuallySet) {
                    orderline.set_discount(porcentajeDescuento);
                }
            }
        }

        this.notification.add(
            _t("Productos y descuentos recalculados automáticamente"),
            { type: "info" }
        );
    }

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

        const allPartners = this.models["res.partner"].getAll();
        console.log(`Cargados ${allPartners.length} contactos al inicio`);

        if (allPartners.length < 1000) {
            try {
                await this.data.loadPartnersBackground();
                const partnersAfterLoad = this.models["res.partner"].getAll();
            } catch (error) {
                console.error("Error al cargar contactos:", error);
            }
        }

        return result;
    },

    async getProductInfo(product, quantity, priceExtra = 0) {
        const order = this.get_order();

        // Mantenemos la llamada al backend para obtener información del producto
        const productInfo = await this.data.call("product.product", "get_product_info_pos", [
            [product.id],
            product.get_price(order.pricelist_id, quantity, priceExtra),
            quantity,
            this.config.id,
        ]);

        // Solo devolvemos la información del producto que contiene datos de stock
        return {
            productInfo,
        };
    },
     get firstScreen() {
        if (odoo.from_backend) {
            const url = new URL(window.location.href);
            url.searchParams.delete("from_backend");
            window.history.replaceState({}, "", url);

            // Asigna el cajero automáticamente si no está asignado
            if (!this.config.module_pos_hr || !this.cashier) {
                this.set_cashier(this.user);
            }
        }
        return "ProductScreen";
    },
    async setup() {
        await originalSetup.call(this, ...arguments);
        // Asigna el cajero automáticamente si no está asignado
        if (this.config.module_pos_hr && !this.cashier) {
            this.set_cashier(this.user);
        }
        this.employeeBuffer = [];
        window.addEventListener("online", () => {
            this.employeeBuffer.forEach((employee) =>
                this.data.write("pos.session", [this.config.current_session_id.id], {
                    employee_id: employee.id,
                })
            );
            this.employeeBuffer = [];
        });
    },
});
