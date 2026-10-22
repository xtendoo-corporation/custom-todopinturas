/** @odoo-module **/

import { PosReceiptClientAction } from "@pos_conventional_core/js/pos_receipt_client_action";
import { patch } from "@web/core/utils/patch";

const THERMAL_REPORT_XMLID = "pos_conventional_receipt_custom.report_factura_simplificada_80mm";

// Ver pos_print_receipt_window_action.js: con PDF no se destruye el iframe
// mientras la previsualizacion de impresion puede seguir abierta.
let lastPdfPrintIframe = null;

patch(PosReceiptClientAction.prototype, {
    _buildReceiptReportUrl(moveId) {
        const params = this.props.action.params || {};
        if (params.is_a4_invoice) {
            return `/todopintura_extend_pos_conventional/invoice_a4/${moveId}`;
        }
        return `/report/html/${THERMAL_REPORT_XMLID}/${moveId}?download=false`;
    },

    _printReportBackground(moveId) {
        window.bypassPosLeave = true;

        const url = this._buildReceiptReportUrl(moveId);
        this._receiptPrintPromise = new Promise((resolve, reject) => {
            const isPdf = !!(this.props.action.params || {}).is_a4_invoice;
            if (isPdf && lastPdfPrintIframe) {
                lastPdfPrintIframe.remove();
                lastPdfPrintIframe = null;
            }
            const iframe = document.createElement("iframe");
            iframe.style.cssText = "position:fixed;left:-2000px;width:1px;height:1px;opacity:0;pointer-events:none;";
            document.body.appendChild(iframe);

            iframe.onload = () => {
                try {
                    setTimeout(() => {
                        try {
                            iframe.contentWindow.focus();
                            const printTitle = (this.props.action.params || {}).print_title;
                            if (printTitle) {
                                document.title = printTitle;
                            }
                            iframe.contentWindow.print();
                            setTimeout(() => {
                                if (isPdf) {
                                    lastPdfPrintIframe = iframe;
                                } else {
                                    iframe.remove();
                                }
                                resolve(true);
                            }, 1200);
                        } catch (error) {
                            iframe.remove();
                            reject(error);
                        }
                    }, 500);
                } catch (error) {
                    iframe.remove();
                    reject(error);
                }
            };

            iframe.onerror = (error) => {
                iframe.remove();
                reject(error);
            };

            iframe.src = url;
        }).catch((error) => {
            console.error("[PosReceiptClientActionPatch] Error printing receipt:", error);
            return false;
        }).finally(() => {
            // Antes, window.bypassPosLeave se quedaba en `true` para siempre
            // tras imprimir (nada lo revertía), desarmando el guard de "no
            // salir de un pedido en borrador" para cualquier pedido abierto
            // después de este, no sólo el recién impreso.
            window.bypassPosLeave = false;
        });

        return this._receiptPrintPromise;
    },

    async closeAction() {
        if (this._receiptPrintPromise) {
            await this._receiptPrintPromise;
        }
        return await super.closeAction(...arguments);
    },
});

