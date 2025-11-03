/** @odoo-module **/
console.info('[todopintura] navbar_patch.js asset executing');

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

// Contador de órdenes creadas
let orderCountNavbar = 0;

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        console.log('[todopintura] ✅ Navbar patched successfully');
    },

    /**
     * Interceptar el clic en el botón de nueva orden
     * Este es el método que se ejecuta al hacer clic en el botón "+"
     */
    async onClickNewOrder() {
        console.log('[todopintura] 🎯 onClickNewOrder interceptado');

        // Verificar si ya hay órdenes creadas
        const hasExistingOrders = orderCountNavbar > 0;
        console.log('[todopintura] Órdenes creadas anteriormente:', orderCountNavbar);

        if (hasExistingOrders) {
            console.log('[todopintura] 🔐 Solicitando cambio de cajero antes de nueva orden');

            // Llamar al método de cambiar cajero nativo
            try {
                await this.onClickCashier();
                console.log('[todopintura] ✅ Cambio de cajero completado');
            } catch (error) {
                console.error('[todopintura] ❌ Error al cambiar cajero:', error);
            }
        }

        // Incrementar contador ANTES de llamar al super
        orderCountNavbar++;
        console.log('[todopintura] ✅ Creando nueva orden. Total:', orderCountNavbar);

        // Llamar al método original
        return await super.onClickNewOrder?.(...arguments);
    },
});

