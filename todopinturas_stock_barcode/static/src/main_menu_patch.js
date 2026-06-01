import { AppMenuItem } from "@web_responsive/components/apps_menu_item/apps_menu_item.esm";
import { XtendooStockBarcodeMainMenu } from "@xtendoo_stock_barcode/main_menu/main_menu";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { onWillStart, useState } from "@odoo/owl";

patch(AppMenuItem.prototype, {
    setup() {
        super.setup(...arguments);
        this.tpState = useState({ tpPendingCount: 0 });
        if (this.props.app.xmlid !== "xtendoo_stock_barcode.menu_xtendoo_stock_barcode_root") {
            return;
        }
        this.orm = useService("orm");
        onWillStart(async () => {
            try {
                this.tpState.tpPendingCount = await this.orm.call(
                    "stock.picking",
                    "get_tp_pending_central_requests_count",
                    []
                );
            } catch {
                this.tpState.tpPendingCount = 0;
            }
        });
    }
});

patch(XtendooStockBarcodeMainMenu.prototype, {
    setup() {
        super.setup(...arguments);
        Object.assign(this.state, useState({ tpPendingRequestsCount: 0 }));
        onWillStart(async () => {
            try {
                this.state.tpPendingRequestsCount = await this.orm.call(
                    "stock.picking",
                    "get_tp_pending_central_requests_count",
                    []
                );
            } catch {
                this.state.tpPendingRequestsCount = 0;
            }
        });
    }
});
