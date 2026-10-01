/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosConventionalOrderFormController } from "@pos_conventional_core/js/pos_order_form_core_controller";
import { activateNavigationBypass, clearNavigationBypass } from "@pos_conventional_core/js/pos_order_workflow_utils";

// activateNavigationBypass()'s own auto-clear (in pos_conventional_core, which
// this module cannot edit) only clears the flag if the URL hash still shows
// the *same* order after its timeout -- if navigation actually succeeded (the
// normal, common case), it never fires and window.bypassPosLeave is left
// `true` indefinitely, silently disarming the "can't leave a draft order with
// products" guard for every order touched afterwards, not just this one.
//
// This debounced backstop guarantees the flag closes within BACKSTOP_MS of
// the *last* relevant click, regardless of where navigation ends up. It's a
// backstop, not the primary mechanism: a real payment/confirm action should
// already finish well within this window, at which point the order's own
// record state (no longer draft / has payments) is what correctly allows
// leaving -- this timer only exists to guarantee the window actually closes.
const BACKSTOP_MS = 2000;
let backstopTimer = null;

function scheduleBypassBackstop() {
    if (backstopTimer) {
        clearTimeout(backstopTimer);
    }
    backstopTimer = setTimeout(() => {
        clearNavigationBypass();
        backstopTimer = null;
    }, BACKSTOP_MS);
}

// Mirrors the button selector pos_order_form_core_controller.js itself reacts
// to, so we know when *its* call to activateNavigationBypass() (with no
// explicit timeout, i.e. the buggy 10s/indefinite one) is about to fire, and
// can schedule our own guaranteed-to-close backstop alongside it.
const CORE_BYPASS_BUTTON_SELECTOR =
    'button[name^="action_pay_"], button[name="action_open_payment_popup"], ' +
    'button[name="action_pos_convention_pay_with_method"], button[name="action_cancel_and_delete_order"], ' +
    '.o_pos_conventional_payment_wizard_form button[name="action_validate"], ' +
    '.o_pos_conventional_payment_wizard_form button[name="action_validate_print"]';

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
            activateNavigationBypass(this.model.root);
            scheduleBypassBackstop();
        }

        const willCoreActivateBypass = ev.target.closest(CORE_BYPASS_BUTTON_SELECTOR);
        const result = super._onPaymentButtonClick(...arguments);
        if (willCoreActivateBypass) {
            scheduleBypassBackstop();
        }
        return result;
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

