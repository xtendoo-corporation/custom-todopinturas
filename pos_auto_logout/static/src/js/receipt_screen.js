/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_screen";
import { useCashierSelector } from "@pos_hr/app/select_cashier_mixin";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// Define el módulo Odoo
odoo.define('pos_auto_logout.CustomReceiptScreen', function(require) {
    const { Component } = require('@odoo/owl');

    class CustomReceiptScreen extends ReceiptScreen {
        setup() {
            console.log("SHINCHAN:"); // Este mensaje debería aparecer en la consola
            super.setup(...arguments);
            // Inicializa el selector de cajeros
            this.cashierSelector = useCashierSelector({
                onCashierChanged: () => this.back(),
                exclusive: true,
            });
        }

        async orderDone() {
            console.log("SHINCHAN2:"); // Este mensaje debería aparecer en la consola
            // Llama al método original
            super.orderDone();

            // Abre el selector de cajeros después de procesar la orden
            this.selectCashier()
                .then((cashier) => {
                    if (cashier) {
                        console.log("Cashier selected:", cashier);
                    } else {
                        console.warn("No cashier selected");
                    }
                })
                .catch((error) => {
                    console.error("Error selecting cashier:", error);
                });
        }

        async selectCashier() {
            return await this.cashierSelector();
        }
    }

    // Registra la nueva clase en la categoría de pantallas
    registry.category("pos_screens").add("CustomReceiptScreen", CustomReceiptScreen);
});
