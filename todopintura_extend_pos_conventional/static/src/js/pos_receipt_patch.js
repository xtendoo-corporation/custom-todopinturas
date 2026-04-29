/** @odoo-module **/

import { PosReceiptClientAction } from "@pos_conventional_core/js/pos_receipt_client_action";
import { patch } from "@web/core/utils/patch";

patch(PosReceiptClientAction.prototype, {
    /**
     * Sobrescribimos el método de impresión para alternar entre el ticket de 80mm
     * y la factura A4 oficial de Odoo según el parámetro 'is_a4_invoice'.
     */
    _printReportBackground(moveId) {
        // Desactivamos el bloqueo de seguridad de navegación ya que el pago es válido
        window.bypassPosLeave = true;
        
        const params = this.props.action.params || {};
        
        if (params.is_a4_invoice) {
            console.log("[PosReceiptClientAction] Printing A4 Invoice (Odoo Standard)");
            const A4_REPORT_XMLID = "account.report_invoice_with_payments";
            const url = `/report/html/${A4_REPORT_XMLID}/${moveId}`;
            
            const iframe = document.body.appendChild(document.createElement("iframe"));
            iframe.style.cssText = "position:fixed;left:-2000px;width:1px;height:1px;";
            
            iframe.onload = () => {
                setTimeout(() => {
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                    setTimeout(() => iframe.remove(), 8000);
                }, 600);
            };
            iframe.src = url;
        } else {
            // Comportamiento normal: Ticket térmico de 80mm
            return super._printReportBackground(...arguments);
        }
    }
});
