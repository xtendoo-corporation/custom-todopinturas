/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("todopintura_closing_popup_methods", {
    steps: () => [
        {
            content: "El popup de cierre muestra los métodos de pago",
            trigger: ".payment-methods-overview:contains('Tarjeta')",
        },
        {
            content: "La cuenta de cliente se llama «Depósito»",
            trigger: ".payment-methods-overview .w-100:contains('Depósito')",
        },
        {
            content: "Ya no aparece con el nombre «Cuenta cliente»",
            trigger: ".payment-methods-overview:not(:contains('Cuenta cliente'))",
        },
        {
            content: "La tarjeta no muestra «Diferencia»",
            trigger: ".payment-methods-overview .w-100:contains('Tarjeta'):not(:has(.border-start))",
        },
        {
            content: "El efectivo sí la mantiene",
            trigger: ".payment-methods-overview .border-start:contains('Diferencia')",
        },
    ],
});
