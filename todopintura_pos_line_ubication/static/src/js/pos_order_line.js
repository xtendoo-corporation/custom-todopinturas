/** @odoo-module */
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup() {
        this.locationData = {
            id: null,
            name: ""
        };
        return super.setup(...arguments);
    },

   set_location(locationId, locationName) {
        this.order_id.assert_editable();

        // Guardar datos en una propiedad separada de los props validados por Owl
        this.locationData = {
            id: locationId ? Number(locationId) : null,
            name: locationName || ""
        };
        this.setDirty();
        return this;
    },

    getDisplayData() {
        const data = super.getDisplayData();
        // Solo incluir la información de ubicación si existe
        if (this.locationData && this.locationData.name) {
            return {
                ...data,
                locationName: this.locationData.name,
            };
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
