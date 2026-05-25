import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { XtendooStockBarcodeMainMenu } from "@xtendoo_stock_barcode/main_menu/main_menu";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

// Patch the HomeMenu (App Switcher) to load the count of pending central requests
patch(HomeMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.tpState = useState({
            pendingCount: 0,
        });
        onWillStart(async () => {
            try {
                this.tpState.pendingCount = await this.orm.call(
                    "stock.picking",
                    "get_tp_pending_central_requests_count",
                    []
                );
            } catch (err) {
                console.error("Failed to load pending central requests count", err);
            }
        });
    }
});

// Patch the Barcode Main Menu to display the count on the Solicitudes Central button
patch(XtendooStockBarcodeMainMenu.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            try {
                this.state.tpPendingRequestsCount = await this.orm.call(
                    "stock.picking",
                    "get_tp_pending_central_requests_count",
                    []
                );
            } catch (err) {
                console.error("Failed to load pending requests count", err);
            }
        });
    }
});
