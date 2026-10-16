/** @odoo-module **/

import { registry } from "@web/core/registry";

function printReceiptInBackground(url, env, { reportAutoprints = false, isPdf = false, printTitle = "" } = {}) {
    // Al imprimir desde un iframe, Chrome propone como nombre de archivo el titulo
    // de la pagina principal; lo cambiamos mientras dura la impresion.
    const previousTitle = document.title;
    if (printTitle) {
        document.title = printTitle;
    }
    return new Promise((resolve) => {
        const iframe = document.createElement("iframe");
        iframe.style.cssText = "position:fixed;left:-2000px;width:1px;height:1px;opacity:0;pointer-events:none;";
        document.body.appendChild(iframe);

        let isSettled = false;

        const cleanup = () => {
            if (isSettled) {
                return;
            }
            isSettled = true;
            iframe.remove();
            document.title = previousTitle;
            window.focus();
            resolve();
        };

        iframe.onload = () => {
            setTimeout(() => {
                if (reportAutoprints) {
                    setTimeout(cleanup, 1200);
                    return;
                }
                try {
                    iframe.contentWindow.focus();
                    if (printTitle) {
                        // El servicio de titulo de Odoo puede haberlo cambiado mientras cargaba
                        document.title = printTitle;
                    }
                    iframe.contentWindow.print();
                } catch (error) {
                    console.error("[PosPrintReceiptWindowAction] Error imprimiendo ticket:", error);
                    env.services.notification.add("No se pudo abrir la impresión del ticket.", {
                        type: "danger",
                        sticky: true,
                    });
                }
                setTimeout(cleanup, 1200);
            }, isPdf ? 1500 : 500); // el visor PDF tarda mas en estar listo
        };

        iframe.onerror = () => {
            env.services.notification.add("No se pudo cargar el ticket para imprimir.", {
                type: "danger",
                sticky: true,
            });
            cleanup();
        };

        iframe.src = url;
    });
}

async function posPrintReceiptWindowAction(env, action) {
    const params = action.params || {};
    const url = params.url;
    const clearBreadcrumbs = params.clear_breadcrumbs !== undefined
        ? !!params.clear_breadcrumbs
        : true;
    if (!url) {
        env.services.notification.add("No se ha proporcionado URL para imprimir.", {
            type: "warning",
        });
        return;
    }

    window.bypassPosLeave = true;

    const absoluteUrl = new URL(url, window.location.origin).toString();
    try {
        await printReceiptInBackground(absoluteUrl, env, {
            reportAutoprints: !!params.report_autoprints,
            isPdf: !!params.is_pdf,
            printTitle: params.print_title || "",
        });

        if (params.next_action) {
            return await env.services.action.doAction(params.next_action, { clearBreadcrumbs });
        }
        return { type: "ir.actions.act_window_close" };
    } finally {
        // Antes nada revertía esto: window.bypassPosLeave se quedaba en
        // `true` para siempre tras imprimir, desarmando el guard de "no
        // salir de un pedido en borrador" para cualquier pedido abierto
        // después de este.
        window.bypassPosLeave = false;
    }
}

registry.category("actions").add(
    "pos_conventional_print_receipt_window",
    posPrintReceiptWindowAction,
    { force: true }
);

