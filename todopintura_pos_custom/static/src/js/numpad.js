import { patch } from "@web/core/utils/patch";
import { Numpad } from "@point_of_sale/app/generic_components/numpad/numpad";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(Numpad.prototype, {
    setup() {
        // Ejecutar setup original
        super.setup();

        // Guardar referencia al método original
        this._originalOnClick = this.onClick;

        // Sobreescribir método onClick
        this.onClick = (buttonValue) => {
            // Detectar si se presiona el botón price
            if (buttonValue === "price") {
                console.log("Botón de precio presionado");
                // Puedes añadir cualquier lógica adicional aquí
            }

            // Llamar al método original
            this._originalOnClick(buttonValue);
        };
    }
});
