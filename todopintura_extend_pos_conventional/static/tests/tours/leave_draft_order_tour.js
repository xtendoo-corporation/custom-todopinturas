/** @odoo-module **/

import { registry } from "@web/core/registry";

const leaveForm = {
    content: "Salir del pedido con el enlace de migas de pan",
    trigger: ".o_breadcrumb .o_back_button, .o_breadcrumb .breadcrumb-item:not(.active) a",
    run: "click",
};

registry.category("web_tour.tours").add("todopintura_leave_draft_order_allowed", {
    steps: () => [
        {
            content: "El formulario del pedido en borrador está abierto",
            trigger: ".o_form_view",
        },
        leaveForm,
        {
            content: "Se sale del pedido sin bloqueo y se llega al listado",
            trigger: ".o_list_view",
        },
    ],
});

registry.category("web_tour.tours").add("todopintura_leave_draft_order_blocked", {
    steps: () => [
        {
            content: "El formulario del pedido en borrador está abierto",
            trigger: ".o_form_view",
        },
        leaveForm,
        {
            content: "Con el ajuste desactivado sale el aviso de pedido sin pago",
            trigger: ".o_notification:contains('No puedes salir de un pedido')",
        },
        {
            content: "Y se sigue en el formulario",
            trigger: ".o_form_view",
        },
    ],
});
