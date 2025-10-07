/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

patch(Navbar.prototype, {
    setup() {
        super.setup?.();
        // Lógica simplificada compatible con Odoo 19
        // En Odoo 19, el cajero se accede directamente como this.pos.cashier
    },
});
