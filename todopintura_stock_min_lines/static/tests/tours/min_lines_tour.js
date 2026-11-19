/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("todopintura_stock_min_lines_pda", {
    steps: () => [
        {
            content: "Diálogo «Seleccionar almacén»",
            trigger: ".modal-footer button[name='action_continue']",
            run: "click",
        },
        {
            content: "La PDA avisa de los productos bajo mínimos cargados",
            trigger: ".alert:contains('bajo mínimos')",
        },
        {
            content: "La línea del producto bajo mínimos está cargada",
            trigger: ".list-group-item:contains('Prod A')",
        },
        {
            content: "Con existencias del destino, mínimo y cantidad a enviar",
            trigger: ".list-group-item:contains('Prod A') .badge:contains('Mínimo'):contains('5')",
        },
        {
            content: "Y la cantidad a enviar",
            trigger: ".list-group-item:contains('Prod A') .badge:contains('A enviar'):contains('4')",
        },
        {
            content: "El producto que no está bajo mínimos no aparece por defecto",
            trigger: "body:not(:has(.list-group-item:contains('Prod B')))",
        },
        {
            content: "Se puede pedir ver también las líneas que no están bajo mínimos",
            trigger: ".alert button:contains('Mostrar 1 línea')",
            run: "click",
        },
        {
            content: "Ahora aparece",
            trigger: ".list-group-item:contains('Prod B')",
        },
        {
            content: "Y se pueden volver a ocultar",
            trigger: ".alert button:contains('Ocultar')",
            run: "click",
        },
        {
            content: "Solo quedan las bajo mínimos",
            trigger: "body:not(:has(.list-group-item:contains('Prod B')))",
        },
    ],
});
