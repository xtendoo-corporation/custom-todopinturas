/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
    },
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        // Aseguramos que pasamos el ID del almacén, ya sea un objeto o un ID directo
        if (this.pickup_warehouse_id) {
            result.pickup_warehouse_id = typeof this.pickup_warehouse_id === 'object' ? this.pickup_warehouse_id.id : this.pickup_warehouse_id;
        }
        return result;
    },
});
