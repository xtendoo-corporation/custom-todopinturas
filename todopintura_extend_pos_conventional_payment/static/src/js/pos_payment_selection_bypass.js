/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosConventionalOrderFormController } from "@pos_conventional_core/js/pos_order_form_core_controller";
import { activateNavigationBypass } from "@pos_conventional_core/js/pos_order_workflow_utils";

patch(PosConventionalOrderFormController.prototype, {
    /**
     * @override
     */
    _onPaymentButtonClick(ev) {
        // Detectar botones de nuestro wizard de selección de pago
        // Los botones de wizard Odoo 19 suelen tener clases específicas o el nombre del método
        const selectionWizardBtn = ev.target.closest(
            '.modal button[name="action_confirm"], .modal button[name="action_deposito"], .modal button[name="action_credito"], .modal button[name="action_albaran"]'
        );

        if (selectionWizardBtn) {
            console.log("[Todopintura] Payment Selection Wizard button clicked, bypassing leave check...");
            activateNavigationBypass(this.model.root);
        }

        return super._onPaymentButtonClick(...arguments);
    },

    /**
     * @override
     * Ampliamos para no bloquear si ya tiene un sale.order vinculado (estado linked)
     */
    _shouldBlockLeavingCurrentOrder(record) {
        if (record && record.data && record.data.state === 'linked') {
            return false;
        }
        return super._shouldBlockLeavingCurrentOrder(...arguments);
    }
});

