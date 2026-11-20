/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("todopintura_customer_item_report_list", {
    steps: () => [
        {
            content: "Asistente de filtros del listado acumulado",
            trigger: ".modal-footer button[name='action_show']",
            run: "click",
        },
        {
            content: "El listado se abre en modo lista, agrupado por clientes",
            trigger: ".o_list_view .o_group_header",
        },
        {
            content: "Agrupado por cliente por defecto: cada cliente es un grupo con sus totales",
            trigger: ".o_group_header:contains('Cliente Alfa CIR'):contains('C-ALFA')",
            run: "click",
        },
        {
            content: "Al abrir el cliente salen sus artículos",
            trigger: ".o_data_row:contains('Articulo A CIR'):contains('CIR-A')",
        },
        {
            content: "El total general queda en el pie de la lista",
            trigger: ".o_list_footer",
        },
        {
            content: "Es un listado de solo lectura: sin botón «Nuevo»",
            trigger: "body:not(:has(.o_list_button_add))",
        },
        {
            content: "Con las columnas pedidas",
            trigger: "th:contains('Precio venta'), th:contains('T. Venta')",
        },
    ],
});
