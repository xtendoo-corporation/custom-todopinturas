import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, useEffect, useState, reactive, onWillRender } from "@odoo/owl";
import { CategorySelector } from "@point_of_sale/app/generic_components/category_selector/category_selector";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import {
    BACKSPACE,
    Numpad,
    getButtons,
    DEFAULT_LAST_ROW,
} from "@point_of_sale/app/generic_components/numpad/numpad";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import {
    ControlButtons,
    ControlButtonsPopup,
} from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { pick } from "@web/core/utils/objects";
import { unaccent } from "@web/core/utils/strings";
import { CameraBarcodeScanner } from "@point_of_sale/app/screens/product_screen/camera_barcode_scanner";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { CustomPricePopup } from "./custom_price_popup";

patch(ProductScreen.prototype, {
    setup() {
        // Primero ejecuta el setup original
        super.setup();

        // Añadimos el hook onMounted para ejecutar _askForPin al cargar
 onMounted(() => {
    const order = this.pos.get_order?.();
    if (order) {
        // Intenta acceder a order.lines
        let lines = [];
        if (order.lines) {
            if (typeof order.lines.toArray === "function") {
                lines = order.lines.toArray();
            } else if (Array.isArray(order.lines)) {
                lines = order.lines;
            }
        }
        console.log("Líneas del pedido:", lines);

        // Ahora puedes usar lines.length para tu lógica
        if (lines.length === 0) {
            setTimeout(() => {
                this._askForPin();
            }, 100);
        }
    } else {
        console.log("No hay pedido activo.");
    }
});

        // Obtener servicios necesarios si no están disponibles
        this.dialog = this.dialog || useService("dialog");
        this.notification = this.notification || useService("notification");
    },
    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]: "o_colorlist_item_color_transparent_6",
            Backspace: "o_colorlist_item_color_transparent_1",
            "-": "o_colorlist_item_color_transparent_3",
        };

        // Usar la misma lógica que se usa para controlar los permisos de precio
        const isBasicUser = !this.pos.cashierHasPriceControlRights();

        console.log("isBasicUser (usando mismo método que para control de precios):", isBasicUser);

        return getButtons(DEFAULT_LAST_ROW, [
            { value: "quantity", text: _t("Qty") },
            { value: "discount", text: _t("%"), disabled: isBasicUser || !this.pos.config.manual_discount },
            {
                value: "price",
                text: _t("Price"),
                disabled: !this.pos.cashierHasPriceControlRights(),
            },
            BACKSPACE,
        ]).map((button) => ({
            ...button,
            class: `
                ${colorClassMap[button.value] || ""}
                ${this.pos.numpadMode === button.value ? "active" : ""}
                ${button.value === "quantity" ? "numpad-qty rounded-0 rounded-top mb-0" : ""}
                ${button.value === "price" ? "numpad-price rounded-0 rounded-bottom mt-0" : ""}
                ${
                    button.value === "discount"
                        ? "numpad-discount my-0 rounded-0 border-top border-bottom"
                        : ""
                }
            `,
        }));
    },
    async _askForPin(intentos = 0) {
        // Limitar intentos para evitar recursión infinita
        if (intentos >= 5) {
            this.notification.add(_t("Demasiados intentos fallidos"), {
                type: "warning",
                title: _t("Error de PIN")
            });
            return;
        }

        try {
            // Mostrar el diálogo de PIN
            const inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Ingrese PIN de cajero"),
            });

            // Si el usuario cancela
            if (!inputPin) {
                this.notification.add(_t("Operación de PIN cancelada"), {
                    type: "info",
                });
                return;
            }

            // Verificar el PIN con los empleados disponibles
            const allEmployees = this.pos.models["hr.employee"];
            const hashedPin = Sha1.hash(inputPin);
            const matchedEmployee = allEmployees.find(
                (employee) => employee._pin === hashedPin
            );

            if (matchedEmployee) {
                // PIN correcto
                this.pos.hasLoggedIn = true;
                this.pos.set_cashier(matchedEmployee);
                this.notification.add(_t("Cajero seleccionado: ") + matchedEmployee.name, {
                    type: "success",
                });
            } else {
                // PIN incorrecto
                this.notification.add(_t("PIN no encontrado"), {
                    type: "warning",
                    title: _t("PIN incorrecto"),
                });

                // Reintento con setTimeout para evitar recursión directa
                setTimeout(() => {
                    this._askForPin(intentos + 1);
                }, 800);
            }
        } catch (error) {
            console.error("Error al procesar el PIN:", error);
            // Reintentar con setTimeout para evitar recursión directa
            setTimeout(() => {
                this._askForPin(intentos + 1);
            }, 800);
        }
    },
async addProductToOrder(product) {
    const order = this.pos.get_order();
    const pricelist = order?.pricelist || this.pos.config.pricelist;
    const partner = order?.partner;
    const price = product.get_price(pricelist, partner);

    console.log("Producto:", product.display_name || product.name);
    console.log("Precio original:", price);

    if (price === 0.01 || price === 0) {
        try {
            // Obtener el precio base (sin descuentos) y calcular porcentaje
            const precioBase = product.lst_price || product.list_price || 0;
            let descuentoInfo = "";

            // Si tenemos un cliente seleccionado, calculamos su descuento
            if (partner && precioBase > 0) {
                // Obtener el precio con descuentos que se aplicaría
                const precioCliente = this.pos.get_price(product, partner, pricelist);
                console.log("Precio cliente:", precioCliente);
                if (precioCliente < precioBase && precioCliente > 0) {
                    const porcentajeDescuento = Math.round((1 - (precioCliente / precioBase)) * 100);
                    console.log("Precio cliente:", precioCliente);
                    console.log("Precio base:", precioBase);
                    console.log("Porcentaje descuento:", porcentajeDescuento);
                    descuentoInfo = ` (Descuento habitual: ${porcentajeDescuento}%)`;
                    console.log("Descuento habitual:", porcentajeDescuento);
                }
            }

            const inputPrice = await makeAwaitable(this.dialog, NumberPopup, {
                title: _t("Ingrese precio para") + ` ${product.display_name || product.name}${descuentoInfo}`,
                startingValue: "",
            });

            if (!inputPrice) {
                this.notification.add(_t("Operación cancelada"), { type: "info" });
                return;
            }

            const precio = parseFloat(inputPrice);
            if (!isNaN(precio) && precio > 0) {
                console.log("Añadiendo producto con precio:", precio);

                const result = await reactive(this.pos).addLineToCurrentOrder({
                    product_id: product.id
                }, {});

                const orderLines = this.pos.get_order().get_orderlines();
                const lastLine = orderLines[orderLines.length - 1];

                if (lastLine) {
                    console.log("Actualizando precio de línea:", lastLine);
                    lastLine.set_unit_price(precio);
                    lastLine.price_manually_set = true;
                    this.pos.get_order().select_orderline(lastLine);
                }

                this.notification.add(_t("Producto añadido con precio personalizado"), { type: "success" });
            } else {
                this.notification.add(_t("Precio inválido"), { type: "warning" });
            }
        } catch (error) {
            console.error("Error en el proceso:", error);
            this.notification.add(_t("Error al procesar el precio"), { type: "danger" });
        }
        return;
    }

    await reactive(this.pos).addLineToCurrentOrder({ product_id: product }, {});
}
});
