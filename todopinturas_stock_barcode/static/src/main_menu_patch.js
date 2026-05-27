import { AppMenuItem } from "@web_responsive/components/apps_menu_item/apps_menu_item.esm";
import { XtendooStockBarcodeMainMenu } from "@xtendoo_stock_barcode/main_menu/main_menu";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

console.log("TODOPINTURAS: main_menu_patch.js loaded");

// Patch the AppMenuItem (App Switcher in web_responsive) to load the count of pending central requests
patch(AppMenuItem.prototype, {
    setup() {
        console.log("TODOPINTURAS: AppMenuItem setup patched");
        super.setup(...arguments);
        this.state = useState({ tpPendingCount: 0 });
        if (this.props.app.xmlid === "xtendoo_stock_barcode.menu_xtendoo_stock_barcode_root") {
            this.orm = useService("orm");
            onWillStart(async () => {
                try {
                    this.state.tpPendingCount = await this.orm.call(
                        "stock.picking",
                        "get_tp_pending_central_requests_count",
                        []
                    );
                    console.log("TODOPINTURAS: AppMenuItem pending requests count:", this.state.tpPendingCount);
                } catch (err) {
                    console.error("Failed to load pending central requests count in AppMenuItem", err);
                }
            });
        }
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
