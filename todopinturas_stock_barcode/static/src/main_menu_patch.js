import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { XtendooStockBarcodeMainMenu } from "@xtendoo_stock_barcode/main_menu/main_menu";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

console.log("TODOPINTURAS: main_menu_patch.js loaded");

// Patch the HomeMenu (App Switcher) to load the count of pending central requests
patch(HomeMenu.prototype, {
    setup() {
        console.log("TODOPINTURAS: HomeMenu setup patched");
        super.setup(...arguments);
        this.orm = useService("orm");
        this.state.tpPendingCount = 0;
        onWillStart(async () => {
            try {
                this.state.tpPendingCount = await this.orm.call(
                    "stock.picking",
                    "get_tp_pending_central_requests_count",
                    []
                );
                console.log("TODOPINTURAS: HomeMenu pending requests count:", this.state.tpPendingCount);
            } catch (err) {
                console.error("Failed to load pending central requests count", err);
            }
        });
    }
});

// Patch the Barcode Main Menu to display the count on the Solicitudes Central button
patch(XtendooStockBarcodeMainMenu.prototype, {
    setup() {
        console.log("TODOPINTURAS: XtendooStockBarcodeMainMenu setup patched");
        super.setup(...arguments);
        this.state.tpPendingRequestsCount = 0;
        onWillStart(async () => {
            try {
                this.state.tpPendingRequestsCount = await this.orm.call(
                    "stock.picking",
                    "get_tp_pending_central_requests_count",
                    []
                );
                console.log("TODOPINTURAS: XtendooStockBarcodeMainMenu pending requests count:", this.state.tpPendingRequestsCount);
            } catch (err) {
                console.error("Failed to load pending requests count", err);
            }
        });
    }
});
