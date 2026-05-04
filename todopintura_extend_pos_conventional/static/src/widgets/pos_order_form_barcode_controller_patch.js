/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const viewRegistry = registry.category("views");
const originalBarcodeFormView = viewRegistry.get("pos_order_barcode_form");

class PosOrderBarcodeFormCreditController extends originalBarcodeFormView.Controller {
    async beforeLeave({ forceLeave } = {}) {
        if (window.bypassPosLeave) {
            return super.beforeLeave(...arguments);
        }

        const record = this.model.root;
        if (record?.data?.state === "draft" && !forceLeave) {
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

