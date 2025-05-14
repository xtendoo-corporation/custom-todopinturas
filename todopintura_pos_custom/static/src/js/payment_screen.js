import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, markup } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

   async _isOrderValid(isForceValidate) {
    console.log("Validando el pedido...");
    // Primero validamos con la lógica original
    if (this.currentOrder.get_orderlines().length === 0 && this.currentOrder.is_to_invoice()) {
        this.dialog.add(AlertDialog, {
            title: _t("Pedido vacío"),
            body: _t(
                "Debe haber al menos un producto en su pedido antes de que pueda ser validado y facturado."
            ),
        });
        return false;
    }

    if ((await this._askForCustomerIfRequired()) === false) {
        return false;
    }

    if (
        (this.currentOrder.is_to_invoice() || this.currentOrder.getShippingDate()) &&
        !this.currentOrder.get_partner()
    ) {
        const confirmed = await ask(this.dialog, {
            title: _t("Por favor seleccione el Cliente"),
            body: _t(
                "Necesita seleccionar el cliente antes de poder facturar o enviar un pedido."
            ),
        });
        if (confirmed) {
            this.pos.selectPartner();
        }
        return false;
    }

    // Mostrar todos los métodos de pago disponibles
    this.logPaymentMethods();

    // Verificamos si hay algún método de pago tipo "cuenta cliente" (pay_later)
    const hasCustomerAccountPayment = this.paymentLines.some(
        line => line.payment_method_id.type === "pay_later"
    );

    // Si usamos cuenta de cliente y tenemos partner, verificamos el crédito
    const partner = this.currentOrder.get_partner();
    if (hasCustomerAccountPayment && partner) {
        try {
            // Llamamos al método del servidor para verificar el límite de crédito
            const orm = this.env.services.orm;
            const creditCheckResult = await orm.call(
                'sale.order',
                'check_credit_limit',  // Usar el método de sale.order
                [partner.id, this.currentOrder.get_total_with_tax()]
            );

            // Si el cliente ha superado el límite de crédito, mostramos el diálogo
            if (creditCheckResult && !creditCheckResult.has_credit) {
                const { confirmed } = await new Promise(resolve => {
                    this.dialog.add(ConfirmationDialog, {
                        title: _t("Límite de crédito excedido"),
                        body: markup(`
                        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px; padding: 16px; margin-bottom: 10px;">
                            <div style="display: flex; gap: 10px; align-items: flex-start; margin-bottom: 12px;">
                                <i class="fa fa-exclamation-triangle" style="font-size: 24px; color: #856404;"></i>
                                <span style="color: #856404; font-size: 16px; font-weight: bold;">${_t("El cliente ")}${creditCheckResult.partner_name}${_t(" ha superado su límite de crédito.")}</span>
                            </div>
                            <div style="margin-left: 34px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                    <span>${_t("Límite de crédito")}:</span>
                                    <span style="font-weight: bold;">${creditCheckResult.credit_limit.toFixed(2)} €</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                    <span>${_t("Crédito ya utilizado")}:</span>
                                    <span style="font-weight: bold;">${creditCheckResult.credit_used.toFixed(2)} €</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                    <span>${_t("Importe del pedido actual")}:</span>
                                    <span style="font-weight: bold;">${creditCheckResult.order_amount.toFixed(2)} €</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; background-color: #ffecb5; padding: 6px; border-radius: 4px; margin-top: 8px;">
                                    <span style="font-weight: bold;">${_t("Total crédito después de confirmar")}:</span>
                                    <span style="font-weight: bold; color: #cc0000;">${creditCheckResult.total_credit.toFixed(2)} €</span>
                                </div>
                            </div>
                        </div>
                        <p style="text-align: center; font-weight: bold; margin-top: 15px;">${_t("¿Desea continuar con el pedido de todas formas?")}</p>
                    `),
                        confirm: () => resolve({ confirmed: true }),
                        cancel: () => resolve({ confirmed: false }),
                    });
                });

                if (!confirmed) {
                    return false; // Cancelar la operación si el usuario no confirma
                }
            }
        } catch (error) {
            console.error("Error al verificar el crédito:", error);
            this.notification.add(_t("Error al verificar el límite de crédito del cliente"), {
                type: "danger",
            });
            return false;
        }
    }

    // Continuamos con el resto de validaciones
    if (this.currentOrder.getShippingDate() &&
        !(partner.name && partner.street && partner.city && partner.country_id)) {
        this.dialog.add(AlertDialog, {
            title: _t("Dirección incorrecta para el envío"),
            body: _t("El cliente seleccionado necesita una dirección."),
        });
        return false;
    }

    if (
        !floatIsZero(
            this.currentOrder.get_total_with_tax(),
            this.pos.currency.decimal_places
        ) &&
        this.currentOrder.payment_ids.length === 0
    ) {
        this.notification.add(_t("Seleccione un método de pago para validar el pedido."));
        return false;
    }

    if (!this.currentOrder.is_paid() || this.invoicing) {
        return false;
    }

    // El resto de la validación se mantiene igual...
    if (
        Math.abs(
            this.currentOrder.get_total_with_tax() -
                this.currentOrder.get_total_paid() +
                this.currentOrder.get_rounding_applied()
        ) > 0.00001
    ) {
        if (!this.pos.models["pos.payment.method"].some((pm) => pm.is_cash_count)) {
            this.dialog.add(AlertDialog, {
                title: _t("No se puede devolver cambio sin un método de pago en efectivo"),
                body: _t(
                    "No hay un método de pago en efectivo disponible en este punto de venta para manejar el cambio.\n\n Por favor, pague la cantidad exacta o añada un método de pago en efectivo en la configuración del punto de venta"
                ),
            });
            return false;
        }
    }

    if (
        !isForceValidate &&
        this.currentOrder.get_total_with_tax() > 0 &&
        this.currentOrder.get_total_with_tax() * 1000 < this.currentOrder.get_total_paid()
    ) {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Por favor confirme la cantidad grande"),
            body:
                _t("¿Está seguro de que el cliente quiere pagar") +
                " " +
                this.env.utils.formatCurrency(this.currentOrder.get_total_paid()) +
                " " +
                _t("por un pedido de") +
                " " +
                this.env.utils.formatCurrency(this.currentOrder.get_total_with_tax()) +
                " " +
                _t('? Al hacer clic en "Confirmar" se validará el pago.'),
            confirm: () => this.validateOrder(true),
        });
        return false;
    }

    if (!this.currentOrder._isValidEmptyOrder()) {
        return false;
    }

    return true;
},
logPaymentMethods() {
    console.log('TODOS LOS MÉTODOS DE PAGO:');
    this.payment_methods_from_config.forEach(method => {
        console.log({
            id: method.id,
            nombre: method.name,
            tipo: method.type,          // Aquí verás "pay_later", "cash", etc.
            secuencia: method.sequence,
            terminal: method.use_payment_terminal ? "Sí" : "No",
            efectivo: method.is_cash_count ? "Sí" : "No"
        });
    });

    // Verificar qué método está seleccionado actualmente
    if (this.paymentLines.length > 0) {
        console.log('LÍNEAS DE PAGO ACTUALES:');
        this.paymentLines.forEach(line => {
            console.log({
                método: line.payment_method_id.name,
                tipo: line.payment_method_id.type,
                importe: line.amount
            });
        });
    }
}
});
