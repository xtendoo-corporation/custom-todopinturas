/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async selectPartner() {
        const result = await super.selectPartner(...arguments);

        if (!result) {
            return result;
        }

        const payload = result;

        // Verificar si el cliente tiene venta a crédito activada
        if (payload.credit_sale) {
            console.log("[CREDIT SALES] Cliente con venta a crédito:", payload.credit_location_id_name);

            try {
                const locationResult = await this.env.services.orm.call(
                    'res.partner',
                    'check_credit_location_matches_pos',
                    [[payload.id], this.config.id]
                );

                console.log("[CREDIT SALES] Resultado verificación de ubicación:", locationResult);

                // Guardar la información de coincidencia en el objeto cliente
                payload.credit_location_mismatch = !locationResult.matches;

                if (!locationResult.matches) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Ubicación incorrecta para venta a crédito"),
                        body: _t(
                            "La ubicación de crédito del cliente (" + locationResult.partner_location_name +
                            ") no coincide con la ubicación de esta caja (" + locationResult.pos_location_name +
                            "). En esta tienda no se puede realizar venta a crédito a este cliente."
                        ),
                    });
                }
            } catch (error) {
                console.error("[CREDIT SALES] Error al verificar ubicación:", error);
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("No se pudo verificar la ubicación de crédito."),
                });
            }
        }

        return result;
    },
});

