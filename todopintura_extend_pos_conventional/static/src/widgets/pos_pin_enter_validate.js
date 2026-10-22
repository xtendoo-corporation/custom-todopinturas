/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";
import { PosPinMaskedField } from "@pos_conventional_users_pin/js/pos_pin_masked_field";

// Pulsar Enter en el campo PIN equivale a pulsar "Validar PIN".
patch(PosPinMaskedField.prototype, {
    setup() {
        super.setup(...arguments);
        useEffect(
            (input) => {
                if (!input) {
                    return;
                }
                const onKeydown = (ev) => {
                    if (ev.key !== "Enter") {
                        return;
                    }
                    ev.preventDefault();
                    // CharField ya confirma el valor con Enter; el click llega despues
                    // para que el boton guarde el PIN recien escrito.
                    setTimeout(() => {
                        const button = input
                            .closest(".modal")
                            ?.querySelector('footer button[name="action_validate_pin"]');
                        if (button && !button.disabled) {
                            button.click();
                        }
                    }, 0);
                };
                input.addEventListener("keydown", onKeydown);
                return () => input.removeEventListener("keydown", onKeydown);
            },
            () => [this.input?.el]
        );
    },
});
