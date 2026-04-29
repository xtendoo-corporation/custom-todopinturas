/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

/**
 * Este script intercepta el clic en los botones de validación del pago
 * para permitir la navegación hacia la pantalla de ticket sin que el 
 * controlador del formulario del pedido bloquee la salida.
 */
document.addEventListener("click", (ev) => {
    const btn = ev.target.closest('button[name="action_validate"], button[name="action_validate_print"]');
    if (btn) {
        // Activamos el bypass temporalmente para permitir la transición tras el pago
        window.bypassPosLeave = true;
        
        // Si después de 10 segundos seguimos en la misma pantalla (error de validación, etc.),
        // restauramos el bloqueo de seguridad.
        setTimeout(() => {
            if (window.bypassPosLeave) {
                window.bypassPosLeave = false;
            }
        }, 10000);
    }
}, true);
