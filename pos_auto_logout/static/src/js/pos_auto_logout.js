/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

patch(ProductScreen.prototype, {
    setup() {
        this.selectedEmployee = null;
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.isMounted = true;
        this.employees = [];

        this.loadEmployees();

        if (ProductScreen.prototype.hasLoadedOnce) {
            this.checkAccessCode();
        } else {
            ProductScreen.prototype.hasLoadedOnce = true;
        }

        return super.setup();
    },

    async checkAccessCode() {
        while (true) {
            const { confirmed, payload: accessCode } = await this.popup.add(NumberPopup, {
                isPassword: true,
                title: _t("Introduce el PIN"),
            });

            console.log("Access code entered:", accessCode);
            const employee = await this.getEmployeeByAccessCode(accessCode);

            if (!confirmed || !employee) {
                await this.popup.add(ErrorPopup, {
                    title: _t("Incorrect Pin"),
                    body: _t("Please try again."),
                });
            } else {
                this.selectedEmployee = employee;
                this.setCashier(employee);
                break;
            }
        }
    },

    async loadEmployees() {
        this.employees = await this.fetchEmployees();
    },

    async getEmployeeByAccessCode(accessCode) {
        try {
            if (!this.isMounted) {
                console.error("Component is destroyed, skipping search");
                return null;
            }
            const employee = this.employees.find(emp => emp.access_code === accessCode);
            console.log("Employee found:", employee);
            return employee || null;
        } catch (error) {
            console.error("Error fetching employee:", error);
            return null;
        }
    },

    async fetchEmployees() {
        try {
            const employees = await this.orm.call('hr.employee', 'search_read', [[], ['id', 'name', 'access_code']]);
            return employees;
        } catch (error) {
            console.error("Error fetching employees:", error);
            return [];
        }
    },

    setCashier(employee) {
        const posStore = this.pos;
        if (posStore) {
            posStore.set_cashier(employee);
            console.log("Cashier set to:", employee);
        } else {
            console.error("PosStore instance not available");
        }
    },
});
