/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();

        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.pos = usePos();

        onMounted(() => {
            this._showPinDialog();
        });
    },

    async _showPinDialog() {
        if (this.pos && this.pos.config.module_pos_hr) {
            // Eliminado el flag _cashierSelectorShown para que aparezca siempre

            // Esperar un poco para que la interfaz esté lista
            setTimeout(() => {
                this._askForPin();
            }, 500);
        }
    },

    async _askForPin() {
        try {
            // Mostrar directamente el diálogo de PIN
            const inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Ingrese PIN de cajero"),
            });

            if (!inputPin) {
                // Si cancela, volver a pedir
                return this._askForPin();
            }

            // Incluir a todos los empleados, incluyendo al cajero actual
            const allEmployees = this.pos.models["hr.employee"];

            // Verificar si algún empleado tiene ese PIN
            const hashedPin = Sha1.hash(inputPin);
            const matchedEmployee = allEmployees.find(
                (employee) => employee._pin === hashedPin
            );

            if (matchedEmployee) {
                // Si encuentra coincidencia, establecer como cajero
                this.pos.hasLoggedIn = true;
                this.pos.set_cashier(matchedEmployee);

                // Mostrar notificación de éxito
                this.notification.add(_t("Cajero seleccionado: ") + matchedEmployee.name, {
                    type: "success",
                });
            } else {
                // Si no encuentra coincidencia, mostrar error y volver a intentar
                this.notification.add(_t("PIN no encontrado"), {
                    type: "warning",
                    title: _t("PIN incorrecto"),
                });

                // Volver a pedir el PIN después de un pequeño retraso
                setTimeout(() => {
                    this._askForPin();
                }, 800);
            }
        } catch (error) {
            console.error("Error al procesar el PIN:", error);
            // Reintentar en caso de error
            this._askForPin();
        }
    },
});
