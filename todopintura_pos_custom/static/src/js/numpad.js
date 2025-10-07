/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Numpad } from "@point_of_sale/app/components/numpad/numpad";

patch(Numpad.prototype, {
    setup() {
        super.setup();

        // Guardar referencia al método original
        this._originalOnClick = this.onClick;

        // Sobreescribir método onClick
        this.onClick = (buttonValue) => {
            if (buttonValue === "price") {
                console.log("Botón de precio presionado");
            }

            // Llamar al método original
            this._originalOnClick(buttonValue);
        };
    }
});
