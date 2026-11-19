/** @odoo-module **/

import { registry } from "@web/core/registry";

const openClosing = [
    {
        content: "Pulsar «Cerrar caja» en el popup de cierre",
        trigger: ".modal-footer button.btn-primary:not([disabled]):contains('Cerrar caja')",
        run: "click",
    },
    {
        content: "Avisa de los pedidos en borrador",
        trigger: ".modal-title:contains('Pedidos en borrador')",
    },
    {
        content: "El aviso lista los pedidos",
        trigger: ".modal-body:contains('Hay pedidos en borrador sin finalizar')",
    },
];

registry.category("web_tour.tours").add("todopintura_closing_discard_draft_orders", {
    steps: () => [
        ...openClosing,
        {
            content: "Borrar los borradores y cerrar la caja",
            trigger: ".modal-footer button:contains('Borrar pedidos en borrador y cerrar caja')",
            run: "click",
        },
        {
            content: "La caja se cierra",
            trigger: ".o_notification:contains('Sesión cerrada correctamente')",
        },
    ],
});

registry.category("web_tour.tours").add("todopintura_closing_keep_draft_orders", {
    steps: () => [
        ...openClosing,
        {
            content: "Volver sin borrar nada",
            trigger: ".modal-footer button:contains('Volver')",
            run: "click",
        },
        {
            content: "Vuelve el popup de cierre, sin cerrar la caja",
            trigger: ".modal-footer button.btn-primary:contains('Cerrar caja')",
        },
        {
            content: "No se ha cerrado: no hay aviso de éxito",
            trigger: "body:not(:has(.o_notification:contains('Sesión cerrada correctamente')))",
        },
    ],
});
