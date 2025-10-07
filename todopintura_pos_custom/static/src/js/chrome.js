/** @odoo-module */
import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";

patch(Chrome.prototype, {
    setup() {
        super.setup();

        // Prevenir navegación hacia atrás
        window.history.pushState(null, null, window.location.href);
        window.addEventListener('popstate', function() {
            window.history.pushState(null, null, window.location.href);
        });

        // Mostrar advertencia si intentan salir o recargar
        const originalBeforeUnload = window.onbeforeunload;
        window.onbeforeunload = (event) => {
            if (originalBeforeUnload) {
                originalBeforeUnload(event);
            }

            if (this.pos && this.pos.get_order()) {
                const message = "¿Seguro que deseas salir?";
                event.returnValue = message;
                return message;
            }
        };
    }
});
