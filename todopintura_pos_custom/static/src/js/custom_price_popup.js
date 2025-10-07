/** @odoo-module */
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { _t } from "@web/core/l10n/translation";

export class CustomPricePopup extends NumberPopup {
    static props = {
        ...NumberPopup.props,
        getPayload: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.title = this.props.title || _t("Ingrese el precio para el producto");
    }
}
