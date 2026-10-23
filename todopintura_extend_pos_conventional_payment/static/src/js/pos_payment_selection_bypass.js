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

// Mientras se confirma el pago y se carga la impresión, el diálogo del wizard
// debe quedar en solo lectura. `inert` bloquea ratón, teclado y foco. Si la
// confirmación falla, Odoo abre un diálogo de error: entonces se desbloquea
// para que se pueda corregir. LOCK_FALLBACK_MS evita que quede bloqueado para
// siempre si algo no cierra el diálogo.
const LOCK_FALLBACK_MS = 30000;
const LOCKABLE_SELECTOR = ".modal-body, .modal-footer";

function lockPaymentWizard(modal) {
    if (!modal || modal.classList.contains("o_todopintura_payment_locked")) {
        return;
    }
    const parts = modal.querySelectorAll(LOCKABLE_SELECTOR);
    modal.classList.add("o_todopintura_payment_locked");
    parts.forEach((el) => el.setAttribute("inert", ""));

    let timer = null;
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === 1 && node !== modal && node.matches?.(".modal")) {
                    unlock();
                    return;
                }
            }
        }
        if (!modal.isConnected) {
            unlock();
        }
    });
    function unlock() {
        observer.disconnect();
        clearTimeout(timer);
        modal.classList.remove("o_todopintura_payment_locked");
        parts.forEach((el) => el.removeAttribute("inert"));
    }
    observer.observe(document.body, { childList: true, subtree: true });
    timer = setTimeout(unlock, LOCK_FALLBACK_MS);
}

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
            const wizardModal = selectionWizardBtn.closest(".modal");
            // Diferido: el clic debe llegar antes al propio botón.
            setTimeout(() => lockPaymentWizard(wizardModal), 0);
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

