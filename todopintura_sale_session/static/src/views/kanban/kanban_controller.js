/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { useService } from "@web/core/utils/hooks";

patch(KanbanController.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        if (!this.headerButtons) {
            this.headerButtons = [];
        }
        this.headerButtons.push({
            id: 'select_employee',
            string: 'Seleccionar Empleado',
            className: 'btn btn-secondary',
            click: this.openEmployeeWizard.bind(this),
        });
    },

    openEmployeeWizard() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Seleccionar Empleado',
            res_model: 'sale.order.employee.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
        });
    }
});
