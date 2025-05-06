/** @odoo-module */
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";

export class LocationLineDialog extends Dialog {
    static template = 'todopintura_pos_custom.LocationLineDialog';
    static components = { Dialog };
    static props = {
        ...Dialog.props,
        locations: { type: Array },
        currentLocationId: { type: Number, optional: true },
        inventoryData: { type: Object },
        confirm: { type: Function },
        slots: { type: Array, optional: true },
        close: { type: Function },
    };

     setup() {
        super.setup();
        this.state = useState({
            selectedLocationId: this.props.currentLocationId ||
                (this.props.locations.length > 0 ? this.props.locations[0].id : null),
        });
    }

    hasStock(locationId) {
        return this.props.inventoryData &&
               this.props.inventoryData[locationId] &&
               this.props.inventoryData[locationId].length > 0;
    }

    getStock(locationId) {
        if (this.hasStock(locationId)) {
            return this.props.inventoryData[locationId][0].quantity || 0;
        }
        return 0;
    }

    onClickConfirm() {
        const selectedLocationId = this.state.selectedLocationId;
        const selectedLocation = this.props.locations.find(loc => loc.id === selectedLocationId);

        if (selectedLocation) {
            this.props.confirm({
                id: Number(selectedLocation.id),
                name: String(selectedLocation.complete_name)
            });
            // Usamos props.close en lugar de this.close
            if (typeof this.props.close === 'function') {
                this.props.close();
            }
        }
    }

    onClickCancel() {
        if (typeof this.props.close === 'function') {
            this.props.close();
        }
    }
}

registry.category("dialogs").add("locationLineDialog", LocationLineDialog);
