/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";

patch(ControlButtons.prototype, {
    async clickPricelist() {
        console.log("Iniciando selección de pricelist...");
        console.log("Pricelist actual:", this.currentOrder.pricelist_id?.name || "Sin pricelist");

        const selectionList = this.getPricelistList();
        console.log("Pricelists disponibles:", selectionList);

        const payload = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Select the pricelist"),
            list: selectionList,
        });

        if (payload) {
            console.log("Nueva pricelist seleccionada:", payload.name);
            this.pos.selectPricelist(payload);
            console.log("Pricelist actualizada a:", this.currentOrder.pricelist_id?.name);
        } else {
            console.log("Selección de pricelist cancelada");
        }
    },
});
