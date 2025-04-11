/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";

patch(ControlButtons.prototype, {
    async clickPricelist() {
        const selectionList = this.getPricelistList();

        const payload = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Select the pricelist"),
            list: selectionList,
        });

        if (payload) {
            this.pos.selectPricelist(payload);
        } else {
            console.log("Selección de pricelist cancelada");
        }
    },
});
