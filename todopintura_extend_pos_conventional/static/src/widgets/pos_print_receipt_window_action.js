/** @odoo-module **/

import { registry } from "@web/core/registry";

function printReceiptInBackground(url, env, { reportAutoprints = false } = {}) {
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
                    iframe.contentWindow.print();
                } catch (error) {
                    console.error("[PosPrintReceiptWindowAction] Error imprimiendo ticket:", error);
                    env.services.notification.add("No se pudo abrir la impresión del ticket.", {
                        type: "danger",
                        sticky: true,
                    });
                }
                setTimeout(cleanup, 1200);
            }, 500);
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
    if (!url) {
        env.services.notification.add("No se ha proporcionado URL para imprimir.", {
            type: "warning",
        });
        return;
    }

    window.bypassPosLeave = true;

    const absoluteUrl = new URL(url, window.location.origin).toString();
    await printReceiptInBackground(absoluteUrl, env, {
        reportAutoprints: !!params.report_autoprints,
    });

    if (params.next_action) {
        return env.services.action.doAction(params.next_action, { clearBreadcrumbs: true });
    }
    return { type: "ir.actions.act_window_close" };
}

registry.category("actions").add(
    "pos_conventional_print_receipt_window",
    posPrintReceiptWindowAction,
    { force: true }
);

