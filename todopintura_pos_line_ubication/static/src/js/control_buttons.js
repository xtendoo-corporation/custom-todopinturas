console.log('control_buttons.js cargado');
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { LocationLineDialog } from "./location_line_dialog";

patch(ControlButtons.prototype, {
    changeUbicationLine() {
        this.trigger('change-ubication-line');
    },
});
