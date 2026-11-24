/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched } from "@odoo/owl";
// Garantiza que la vista base ya está registrada antes de parchearla (también en los
// tests HOOT, que solo cargan los módulos que se importan).
import "@pos_conventional_order_barcode/js/pos_order_form_barcode_controller";

const viewRegistry = registry.category("views");
const originalBarcodeFormView = viewRegistry.get("pos_order_barcode_form");

class PosOrderBarcodeFormCreditController extends originalBarcodeFormView.Controller {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this._lastPartnerId = false;
        this._pendingCreditWarningPartnerId = false;
        this._previousPartnerIdForWarning = false;
        this._openingCreditWarning = false;

        onMounted(() => {
            this._lastPartnerId = this._getCurrentPartnerId();
        });

        onPatched(() => {
            this._handlePartnerCreditWarning();
        });
    }

    _extractMany2OneId(value) {
        if (!value) {
            return false;
        }
        if (Array.isArray(value)) {
            return value[0] || false;
        }
        if (typeof value === "object") {
            return value.resId || value.id || false;
        }
        return false;
    }

    _getCurrentPartnerId() {
        return this._extractMany2OneId(this.model.root?.data?.partner_id);
    }

    async _handlePartnerCreditWarning() {
        const record = this.model.root;
        const currentPartnerId = this._getCurrentPartnerId();

        if (currentPartnerId !== this._lastPartnerId) {
            this._previousPartnerIdForWarning = this._lastPartnerId || false;
            this._lastPartnerId = currentPartnerId || false;
            this._pendingCreditWarningPartnerId = currentPartnerId || false;
        }

        if (
            !record?.resId ||
            !this._pendingCreditWarningPartnerId ||
            this._pendingCreditWarningPartnerId !== currentPartnerId ||
            this._openingCreditWarning
        ) {
            return;
        }

        if (
            record.data?.state !== "draft" ||
            record.data?.is_linked_to_sale ||
            !record.data?.partner_credit_available
        ) {
            return;
        }

        this._openingCreditWarning = true;
        try {
            const action = await this.orm.call(
                "pos.order",
                "action_open_partner_credit_cashier_warning",
                [record.resId, this._previousPartnerIdForWarning || false]
            );
            this._pendingCreditWarningPartnerId = false;
            if (action) {
                await this.actionService.doAction(action);
            }
        } catch (error) {
            console.error(
                "No se pudo abrir el wizard de aviso de crédito al seleccionar el cliente.",
                error
            );
        } finally {
            this._openingCreditWarning = false;
        }
    }

    async beforeLeave({ forceLeave } = {}) {
        if (window.bypassPosLeave) {
            return super.beforeLeave(...arguments);
        }

        const record = this.model.root;
        // Con «Permitir ventas en borrador» (ajuste del TPV) se puede salir sin pagar.
        if (record?.data?.state === "draft" && !forceLeave && !record.data.allow_draft_orders) {
            const orderId = record.resId;
            if (orderId) {
                try {
                    const hasDraftPayLaterPayment = await this.orm.call(
                        "pos.order",
                        "has_draft_pay_later_payment",
                        [orderId]
                    );
                    if (hasDraftPayLaterPayment) {
                        return super.beforeLeave(...arguments);
                    }
                } catch (error) {
                    console.warn(
                        "No se pudo comprobar si el pedido borrador tiene cuenta cliente.",
                        error
                    );
                }
            }

            this._playErrorBeep();
            this.notification.add(
                _t(
                    "No puedes salir de un pedido que no ha sido pagado. Por favor, finaliza el pago, cancélalo o elimínalo antes de salir."
                ),
                {
                    type: "warning",
                    title: _t("Pedido no pagado"),
                    sticky: false,
                    autocloseDelay: 10000,
                }
            );
            return false;
        }

        return super.beforeLeave(...arguments);
    }
}

viewRegistry.add(
    "pos_order_barcode_form",
    {
        ...originalBarcodeFormView,
        Controller: PosOrderBarcodeFormCreditController,
    },
    { force: true }
);

