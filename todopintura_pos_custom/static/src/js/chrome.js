import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";

// Guardamos referencia al setup original ANTES de hacer el patch
const originalSetup = Chrome.prototype.setup;

// Aplicamos el patch usando la referencia guardada
patch(Chrome.prototype, {
    setup() {
        // Llamamos al método setup original usando la referencia
        originalSetup.call(this);

        // Prevenir navegación hacia atrás
        window.history.pushState(null, null, window.location.href);
        window.addEventListener('popstate', function() {
            window.history.pushState(null, null, window.location.href);
        });

        // Mostrar advertencia si intentan salir o recargar
        const originalBeforeUnload = window.onbeforeunload;
        window.onbeforeunload = (event) => {
            // Preservar comportamiento original
            if (originalBeforeUnload) {
                originalBeforeUnload(event);
            }

            // Prevenir salida si hay una orden activa
            if (this.pos && this.pos.get_order()) {
                const message = "¿Seguro que deseas salir?";
                event.returnValue = message;
                return message;
            }
        };
    }
});
