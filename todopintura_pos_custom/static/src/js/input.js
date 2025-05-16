// todopintura_pos_custom/static/src/js/input.js
import { patch } from "@web/core/utils/patch";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";

patch(Input.prototype, {
    setup() {
        // Llamamos al método original usando super
        super.setup();

        // Añadimos nuestro estado de escritura
        this.state.isTyping = false;

        // Reemplazamos onPatched
        if (this.__owl__.hooks && this.__owl__.hooks.onPatched) {
            const originalHooks = [...this.__owl__.hooks.onPatched];
            this.__owl__.hooks.onPatched = [
                () => {
                    if (!this.state.isTyping) {
                        this.setValue.cancel(true);
                    } else {
                        // Si estamos escribiendo, no cancelamos el debounce
                    }
                }
            ];
        }
    },

    onFocus() {
        this.state.isTyping = true;
    },

    onBlur() {
        this.state.isTyping = false;
    },

    setValue(newValue, tModel) {
        this.state.isTyping = true;

        // Llamamos al método original usando super
        super.setValue(newValue, tModel || this.props.tModel);

        // Restauramos el estado después de un tiempo
        setTimeout(() => {
            this.state.isTyping = false;
        }, 100);
    }
});
