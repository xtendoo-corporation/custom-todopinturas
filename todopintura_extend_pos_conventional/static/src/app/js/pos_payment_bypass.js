/** @odoo-module **/

/**
 * Este script intercepta el clic en los botones de validación del pago
 * para permitir la navegación hacia la pantalla de ticket sin que el
 * controlador del formulario del pedido bloquee la salida.
 *
 * OJO: "action_open_payment_selection_wizard" se quitó deliberadamente de
 * aquí -- ese botón sólo ABRE el wizard de selección de pago (un diálogo
 * modal, target "new"), no termina el pedido. Concederle bypass dejaba una
 * ventana de 10s para abandonar el pedido justo al pulsar "Pago", antes
 * incluso de intentar cobrar nada. Sólo los botones que de verdad completan
 * el pedido (confirmar / validar) deben conceder esta ventana.
 */
document.addEventListener("click", (ev) => {
    const btn = ev.target.closest('button[name="action_validate"], button[name="action_validate_print"], button[name="action_confirm"]');
    if (btn) {
        // Activamos el bypass temporalmente para permitir la transición tras el pago.
        // Antes: 10s. Una vez que el pedido se confirma, su propio estado
        // (ya no "draft" / con pagos registrados) es lo que legítimamente
        // permite salir -- esta ventana sólo cubre el breve hueco mientras la
        // respuesta del servidor todavía no se ha reflejado localmente.
        window.bypassPosLeave = true;

        // Si tras ese margen seguimos en la misma pantalla (error de validación, etc.),
        // restauramos el bloqueo de seguridad incondicionalmente.
        setTimeout(() => {
            window.bypassPosLeave = false;
        }, 2000);
    }
}, true);
