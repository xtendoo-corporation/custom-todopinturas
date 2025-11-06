/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { CouponAndAssignedPeopleDialog } from "./coupon_and_assigned_people";

patch(PosStore.prototype, {
    async selectPartner() {
        const result = await super.selectPartner(...arguments);

        if (!result) {
            return result;
        }

        const payload = result;

        // Verificar si el cliente tiene personas asignadas o vales
        const tienePersonasAsignadas = payload.assigned_persons_info;
        const tieneVales = payload.voucher;

        // Mostrar el diálogo si tiene personas asignadas O vales
        if (tienePersonasAsignadas || tieneVales) {
            try {
                await new Promise(resolve => {
                    this.dialog.add(CouponAndAssignedPeopleDialog, {
                        partner: payload,
                        assignedPeopleInfo: tienePersonasAsignadas || false,
                        confirm: resolve,
                        close: () => resolve(false)
                    });
                });
            } catch (error) {
                console.error("[PARTNER INFO] Error al mostrar el diálogo:", error);
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("No se pudo mostrar el diálogo de información del cliente."),
                });
            }
        }

        return result;
    },
});

