/** @odoo-module **/

import { QtyAtDateWidget, QtyAtDatePopover, qtyAtDateWidget } from "@sale_stock/widgets/qty_at_date_widget";
import { registry } from "@web/core/registry";

export class PosQtyAtDatePopover extends QtyAtDatePopover {
    static template = "todopintura_extend_pos_conventional.PosQtyAtDatePopover";

    openForecast() {
        return false;
    }

    get stockAtLocations() {
        try {
            return JSON.parse(this.props.record.data.stock_at_locations_json || "[]");
        } catch (e) {
            return [];
        }
    }

    get totalStock() {
        return this.stockAtLocations.reduce((acc, loc) => acc + loc.qty, 0);
    }
}

export class PosQtyAtDateWidget extends QtyAtDateWidget {
    static components = { Popover: PosQtyAtDatePopover };
}

export const posQtyAtDateWidget = {
    ...qtyAtDateWidget,
    component: PosQtyAtDateWidget,
    fieldDependencies: [
        ...(qtyAtDateWidget.fieldDependencies || []),
        { name: "stock_at_locations_json", type: "text" },
    ],
};

registry.category("view_widgets").add("pos_qty_at_date_widget", posQtyAtDateWidget);
