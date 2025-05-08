/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { floatIsZero } from "@web/core/utils/numbers";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        console.log("Validando orden con ubicaciones...");

        // Verificar si hay líneas con ubicaciones antes de validar
        const orderLinesWithLocation = this.currentOrder.get_orderlines().filter(line =>
            line.locationData && line.locationData.id && line.locationData.name
        );

        console.log("Número de líneas con ubicación:", orderLinesWithLocation.length);
        if (orderLinesWithLocation.length > 0) {
            console.log("Ubicaciones encontradas:");
            orderLinesWithLocation.forEach(line => {
                console.log(`Producto: ${line.get_product().display_name}, Ubicación: ${line.locationData.name} (ID: ${line.locationData.id})`);
            });
        } else {
            console.log("No se encontraron líneas con ubicación");
        }

        this.numberBuffer.capture();
        if (!this.check_cash_rounding_has_been_well_applied()) {
            return;
        }
        const linesToRemove = this.currentOrder.lines.filter((line) => {
            const rounding = line.product_id.uom_id.rounding;
            const decimals = Math.max(0, Math.ceil(-Math.log10(rounding)));
            return floatIsZero(line.qty, decimals);
        });
        for (const line of linesToRemove) {
            this.currentOrder.removeOrderline(line);
        }
        if (await this._isOrderValid(isForceValidate)) {
            // Verificar ubicaciones nuevamente después de validar
            console.log("Orden válida, verificando ubicaciones después de validación...");
            const orderLinesWithLocationAfterValidation = this.currentOrder.get_orderlines().filter(line =>
                line.locationData && line.locationData.id && line.locationData.name
            );
            console.log("Líneas con ubicación después de validación:", orderLinesWithLocationAfterValidation.length);

            // remove pending payments before finalizing the validation
            const toRemove = [];
            for (const line of this.paymentLines) {
                if (!line.is_done() || line.amount === 0) {
                    toRemove.push(line);
                }
            }

            for (const line of toRemove) {
                this.currentOrder.remove_paymentline(line);
            }
            await this._finalizeValidation();
        }
    }
});
