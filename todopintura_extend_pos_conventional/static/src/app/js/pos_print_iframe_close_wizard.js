/** @odoo-module **/

import { registry } from "@web/core/registry";
import { openUrlInHiddenPrintIframe } from "@pos_conventional_core/js/pos_print_iframe";

const printIframeAction = async (env, action) => {
    const params = action.params || {};

    if (params.url) {
        try {
            await openUrlInHiddenPrintIframe(params.url);
        } catch (error) {
            console.error("Error al imprimir iframe (todopintura override):", error);
            env.services.notification.add("Error al imprimir el documento.", {
                type: "danger",
            });
        }
    }

    // Asegurarnos de cerrar cualquier diálogo/modal (wizard de selección de pago)
    try {
        env.services.dialog && env.services.dialog.closeAll && env.services.dialog.closeAll();
    } catch (e) {
        console.warn("todopintura: No se pudo cerrar diálogos antes de ejecutar next_action:", e);
    }

    if (params.next_action) {
        return env.services.action.doAction(params.next_action);
    }

    return { type: "ir.actions.act_window_close" };
};

// Registramos con force para que sustituya la acción original y así cerrar el wizard
registry.category("actions").add("pos_conventional_print_iframe", printIframeAction, { force: true });

