/** @odoo-module **/
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";

export class LocationSelectionDialog extends Dialog {
    static template = 'todopintura_pos_custom.LocationSelectionDialog';
    static components = { Dialog };
    static props = {
        ...Dialog.props,
        locations: { type: Array, optional: true },
        inventoryData: { type: Object, optional: true },
        orderProducts: { type: Array, optional: true },
        bodyMessage: { type: String, optional: true },
        onConfirm: { type: Function },
        onCancel: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.state = useState({
            selectedLocationId: null
        });
    }

    onLocationChange(ev) {
        this.state.selectedLocationId = parseInt(ev.target.value);
    }

    getSelectedLocation() {
        if (!this.state.selectedLocationId || !this.props.locations) {
            return null;
        }
        return this.props.locations.find(loc => loc.id === this.state.selectedLocationId);
    }

    onClickConfirm() {
        const selectedLocation = this.getSelectedLocation();
        if (selectedLocation) {
            this.props.onConfirm(selectedLocation);
        }
        this.props.close();
    }

    onClickCancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
        this.props.close();
    }
}

registry.category("dialogs").add("locationSelectionDialog", LocationSelectionDialog);
