/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useCashierSelector } from "@pos_hr/app/select_cashier_mixin";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup();
        this.cashierSelector = useCashierSelector({
            onCashierChanged: (cashier) => this.handleCashierChange(cashier),
            exclusive: true,
        });
    },

    async orderDone() {
        const cashierSelected = await this.selectCashier();
        if (cashierSelected) {
            super.orderDone();
        } else {
            super.orderDone();
        }
    },

    async selectCashier() {
        return new Promise((resolve) => {
            this.cashierSelector().then((cashier) => {
                if (cashier) {
                    resolve(true);
                } else {
                    resolve(false);
                }
            }).catch((error) => {
                resolve(false);
            });
        });
    },

    handleCashierChange(cashier) {
    },
});
