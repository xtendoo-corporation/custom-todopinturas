/** @odoo-module **/
console.info('[todopintura] chrome.js asset executing');
window.__TODOPINTURA_CHROME_LOADED = true;
import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";
import { onWillUnmount, onMounted } from "@odoo/owl";

// Guardamos referencia al setup original ANTES de hacer el patch
const originalSetup = Chrome.prototype.setup;

// Aplicamos el patch usando la referencia guardada
patch(Chrome.prototype, {
    setup() {
        // Llamamos al método setup original usando la referencia
        originalSetup.apply(this, arguments);

        console.debug('[todopintura] Chrome patched - setup called');

        // Variables para restaurar
        let popHandler = null;
        let originalBeforeUnload = null;

        onMounted(() => {
            console.debug('[todopintura] Chrome onMounted - attaching handlers');
            // Prevenir navegación hacia atrás
            popHandler = () => {
                window.history.pushState(null, null, window.location.href);
            };
            try {
                window.history.pushState(null, null, window.location.href);
                window.addEventListener('popstate', popHandler);
            } catch (e) {
                console.error('Error añadiendo listener popstate:', e);
            }

            // Mostrar advertencia si intentan salir o recargar
            try {
                originalBeforeUnload = window.onbeforeunload;
            } catch (e) {
                originalBeforeUnload = null;
            }

            const beforeUnloadHandler = (event) => {
                try {
                    // Preservar comportamiento original si era función
                    if (originalBeforeUnload && typeof originalBeforeUnload === 'function') {
                        const originalResult = originalBeforeUnload.call(window, event);
                        if (originalResult) {
                            return originalResult;
                        }
                    }
                } catch (e) {
                    console.error('Error al ejecutar onbeforeunload original:', e);
                }

                // Prevenir salida si hay una orden activa
                try {
                    if (this.pos && typeof this.pos.get_order === 'function' && this.pos.get_order()) {
                        const message = "¿Seguro que deseas salir?";
                        event.returnValue = message;
                        return message;
                    }
                } catch (e) {
                    console.error('Error comprobando orden activa en beforeunload:', e);
                }
                return undefined;
            };

            try {
                window.onbeforeunload = beforeUnloadHandler;
            } catch (e) {
                console.error('Error asignando onbeforeunload:', e);
            }
        });

        // Limpiar listeners cuando el componente se desmonte
        onWillUnmount(() => {
            try {
                if (popHandler) {
                    window.removeEventListener('popstate', popHandler);
                }
            } catch (e) {
                // ignore
            }
            try {
                window.onbeforeunload = originalBeforeUnload;
            } catch (e) {
                // ignore
            }
        });
    }
});
