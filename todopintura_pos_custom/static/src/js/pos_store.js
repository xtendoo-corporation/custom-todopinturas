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
    }
});
