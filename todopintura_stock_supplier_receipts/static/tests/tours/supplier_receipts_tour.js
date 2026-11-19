/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("todopintura_supplier_receipts_main_menu", {
    steps: () => [
        {
            content: "Menú principal de Transferencias internas",
            trigger: ".o_xtendoo_stock_barcode button:contains('Entradas')",
            run: "click",
        },
        {
            content: "Se pregunta por el proveedor",
            trigger: ".modal-title:contains('Entradas de proveedor')",
        },
        {
            content: "Con la lista de entradas clásica disponible",
            trigger: ".modal-footer button[name='action_open_list']",
        },
    ],
});

registry.category("web_tour.tours").add("todopintura_supplier_receipts_pda", {
    steps: () => [
        {
            content: "Continuar con el proveedor elegido",
            trigger: ".modal-footer button[name='action_continue']",
            run: "click",
        },
        {
            content: "Aviso con el proveedor y sus recepciones",
            trigger: ".alert:contains('Proveedor Uno')",
        },
        {
            content: "Línea del proveedor",
            trigger: ".list-group-item:contains('Prod P1')",
        },
        {
            content: "Otra línea del proveedor",
            trigger: ".list-group-item:contains('Prod P2')",
        },
        {
            content: "No aparecen las líneas de otros proveedores",
            trigger: "body:not(:has(.list-group-item:contains('Prod P3')))",
        },
    ],
});
