/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { XtendooStockBarcodePickingClientAction } from "@xtendoo_stock_barcode/client_action/picking_client_action";

patch(XtendooStockBarcodePickingClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        // Por defecto solo se ven las líneas bajo mínimos.
        this.state.tpShowAll = false;
    },

    tpToggleAll() {
        this.state.tpShowAll = !this.state.tpShowAll;
    },
});
