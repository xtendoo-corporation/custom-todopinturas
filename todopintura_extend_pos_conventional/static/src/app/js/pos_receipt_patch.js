/** @odoo-module **/

import { PosReceiptClientAction } from "@pos_conventional_core/js/pos_receipt_client_action";
import { patch } from "@web/core/utils/patch";

patch(PosReceiptClientAction.prototype, {
    /**
     * Sobrescribimos el método de impresión para alternar entre el ticket de 80mm
     * y la factura A4 oficial de Odoo según el parámetro 'is_a4_invoice'.
     */
    _printReportBackground(moveId) {
        // Desactivamos el bloqueo de seguridad de navegación ya que el pago es válido.
        // OJO: antes esto nunca se revertía -- window.bypassPosLeave se quedaba
        // en `true` para siempre tras imprimir una factura A4, desarmando el
        // guard de "no salir de un pedido en borrador" para CUALQUIER pedido
        // que se abriera después, no sólo este. Ahora se limpia de forma
        // determinista en cuanto termina el propio flujo de impresión.
        window.bypassPosLeave = true;

        const params = this.props.action.params || {};

        if (params.is_a4_invoice) {
            const A4_REPORT_XMLID = "account.report_invoice_with_payments";
            const url = `/report/html/${A4_REPORT_XMLID}/${moveId}`;

            const iframe = document.body.appendChild(document.createElement("iframe"));
            iframe.style.cssText = "position:fixed;left:-2000px;width:1px;height:1px;";

            const clearBypass = () => {
                window.bypassPosLeave = false;
            };

            iframe.onload = () => {
                setTimeout(() => {
                    try {
                        iframe.contentWindow.focus();
                        iframe.contentWindow.print();
                    } finally {
                        setTimeout(() => {
                            iframe.remove();
                            clearBypass();
                        }, 8000);
                    }
                }, 600);
            };
            iframe.onerror = () => {
                iframe.remove();
                clearBypass();
            };
            iframe.src = url;
        } else {
            // Comportamiento normal: Ticket térmico de 80mm
            return super._printReportBackground(...arguments);
        }
    }
});
