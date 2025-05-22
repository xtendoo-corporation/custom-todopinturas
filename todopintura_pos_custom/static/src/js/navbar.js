import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { useEffect } from "@odoo/owl";

patch(Navbar.prototype, {
    setup() {
        super.setup?.();
        this.updateIsBasicUser = () => {
            const basicIds = (this.pos.config.basic_employee_ids || []).map(e => e.id || e);
            const cashier = this.pos.get_cashier();
            this.isBasicUser = cashier && basicIds.includes(cashier.id);
        };
        this.updateIsBasicUser();

        useEffect(
            () => {
                this.updateIsBasicUser();
            },
            () => [this.pos.get_cashier?.() && this.pos.get_cashier().id]
        );
    },
});
