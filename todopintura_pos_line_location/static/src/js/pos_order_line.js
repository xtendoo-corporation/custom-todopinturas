/** @odoo-module */
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.locationData = {
            id: null,
            name: ""
        };
    },

    set_location(locationId, locationName) {
        // Guardar datos de ubicación
        this.locationData = {
            id: locationId ? Number(locationId) : null,
            name: locationName || ""
        };

        // En Odoo 19, marcar como dirty se hace automáticamente al modificar propiedades
        if (this._dirty !== undefined) {
            this._dirty = true;
        }

        return this;
    },

    getDisplayData() {
        const data = super.getDisplayData();
        if (this.locationData && this.locationData.name) {
            data.locationName = this.locationData.name;
        }
        return data;
    },

    export_as_JSON() {
        const json = super.export_as_JSON();
        return {
            ...json,
            location_id: this.locationData?.id || false,
        };
    },
});
