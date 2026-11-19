/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("todopintura_employee_pin_new_order", {
    steps: () => [
        {
            content: "Diálogo de PIN de empleado",
            trigger: ".modal:contains('PIN de empleado')",
        },
        {
            content: "Escribir el PIN del empleado",
            trigger: ".modal .o_pos_pin_masked_input, .modal input",
            run: "edit 4711",
        },
        {
            content: "Validar el PIN",
            trigger: ".modal-footer button[name='action_validate_pin']",
            run: "click",
        },
        {
            content: "Se abre el pedido nuevo",
            trigger: ".o_form_view .o_form_sheet, .o_form_view",
        },
    ],
});
