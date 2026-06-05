/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, xml } from "@odoo/owl";

export class TodopinturaStockPickingBarcodeRefreshField extends Component {
    static props = { ...standardFieldProps };
    static supportedTypes = ["char"];
    static template = xml`<div class="d-none"/>`;

    setup() {
        this.barcode = useService("barcode");
        this.isProcessing = false;
        useBus(this.barcode.bus, "barcode_scanned", this.onBarcodeScanned.bind(this));
        try {
            console.log("TODOPINTURA: StockPickingBarcodeRefreshField setup", {
                resModel: this.props.record?.resModel,
                resId: this.props.record?.resId,
            });
        } catch (err) {
            console.warn("TODOPINTURA: Could not log StockPickingBarcodeRefreshField setup", err);
        }
    }

    async onBarcodeScanned(event) {
        const { barcode } = event.detail;
        if (!barcode || this.isProcessing || !this.props.record?.resId) {
            return;
        }
        this.isProcessing = true;
        try {
            // Recargar el record raíz del formulario para que la vista muestre los cambios
            if (this.props.record?.model?.root) {
                await this.props.record.model.root.load();
            } else if (this.props.record?.load) {
                await this.props.record.load();
            }
        } catch (err) {
            console.error("TODOPINTURA: Error reloading record from field component:", err);
        } finally {
            this.isProcessing = false;
        }
    }
}

registry.category("fields").add("todopintura_stock_barcode_refresh", {
    component: TodopinturaStockPickingBarcodeRefreshField,
});

