/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { XtendooStockBarcodeMainMenu } from "@xtendoo_stock_barcode/main_menu/main_menu";
import { XtendooStockBarcodePickingClientAction } from "@xtendoo_stock_barcode/client_action/picking_client_action";

// «Entradas»: primero se pregunta el proveedor.
patch(XtendooStockBarcodeMainMenu.prototype, {
    async openIncomingAction() {
        return this.actionService.doAction(
            "todopintura_stock_supplier_receipts.action_stock_barcode_supplier_wizard"
        );
    },
});

// PDA de entradas por proveedor: todas las llamadas llevan el proveedor en el contexto,
// así el servidor solo ve y procesa sus recepciones pendientes.
patch(XtendooStockBarcodePickingClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        const supplierId = this.props.action.params.partner_id;
        if (supplierId) {
            const orm = this.orm;
            this.orm = new Proxy(orm, {
                get(target, prop) {
                    if (prop === "call") {
                        return (model, method, args = [], kwargs = {}) =>
                            target.call(model, method, args, {
                                ...kwargs,
                                context: { ...(kwargs.context || {}), tp_supplier_id: supplierId },
                            });
                    }
                    const value = target[prop];
                    return typeof value === "function" ? value.bind(target) : value;
                },
            });
        }
    },
});
