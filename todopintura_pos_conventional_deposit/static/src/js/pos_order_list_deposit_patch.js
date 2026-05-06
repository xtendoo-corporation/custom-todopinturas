/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrderListController } from "@pos_conventional_core/js/pos_order_list_controller";

const superActionMenuItems = Object.getOwnPropertyDescriptor(
    PosOrderListController.prototype,
    "actionMenuItems"
);

patch(PosOrderListController.prototype, {
    async onOpenDepositPaymentWizard() {
        const sessionId = this.currentSessionId || this.activeSessionId;
        if (!sessionId) {
            return;
        }
        const action = await this.model.orm.call(
            "pos.order",
            "action_open_deposit_payment_wizard",
            [],
            {
                context: {
                    ...(this.props.context || {}),
                    default_session_id: sessionId,
                    session_id: sessionId,
                },
            }
        );
        return this.actionService.doAction(action);
    },

    get actionMenuItems() {
        const items = superActionMenuItems?.get
            ? superActionMenuItems.get.call(this)
            : { action: [] };

        if (!this.state.showCloseButton) {
            return items;
        }

        items.action = items.action || [];
        if (!items.action.find((item) => item.key === "deposit_payments")) {
            items.action.push({
                key: "deposit_payments",
                description: "Pagar depósitos",
                icon: "fa fa-archive",
                callback: () => this.onOpenDepositPaymentWizard(),
                sequence: 105,
            });
        }
        return items;
    },
});

