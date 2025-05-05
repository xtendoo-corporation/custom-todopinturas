/** @odoo-module */
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

console.log("🔍 Cargando patch para PosOrderline con soporte de ubicaciones...");

patch(PosOrderline.prototype, {
    // Asignar ubicación a una línea
    set_location(locationId, locationName) {
        this.locationId = locationId;
        this.locationName = locationName;
        this.setDirty();
        this.set_quantity(this.get_quantity(), true);
        return this;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);

        if (this.locationId) {
            json.locationId = this.locationId;
        }
        if (this.locationName) {
            json.locationName = this.locationName;
        }

        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);

        if (json.locationId) {
            this.locationId = json.locationId;
        }
        if (json.locationName) {
            json.locationName = json.locationName;
        }
    }
});

console.log("✅ Patch de PosOrderline aplicado correctamente");
