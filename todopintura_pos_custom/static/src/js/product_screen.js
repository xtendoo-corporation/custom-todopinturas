/** @odoo-module */
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { onMounted } from "@odoo/owl";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { CustomPricePopup } from "./custom_price_popup";
import { getButtons, DEFAULT_LAST_ROW, BACKSPACE } from "@point_of_sale/app/components/numpad/numpad";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();

        // Añadimos el hook onMounted para ejecutar _askForPin al cargar
        onMounted(() => {
            const order = this.pos.get_order?.();
            if (order) {
                let lines = [];
                if (order.lines) {
                    if (typeof order.lines.toArray === "function") {
                        lines = order.lines.toArray();
                    } else if (Array.isArray(order.lines)) {
                        lines = order.lines;
                    }
                }
                console.log("Líneas del pedido:", lines);

                if (lines.length === 0) {
                    setTimeout(() => {
                        this._askForPin();
                    }, 100);
                }
            } else {
                console.log("No hay pedido activo.");
            }
        });

        this.dialog = this.dialog || useService("dialog");
        this.notification = this.notification || useService("notification");
    },

    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]: "o_colorlist_item_color_transparent_6",
            Backspace: "o_colorlist_item_color_transparent_1",
            "-": "o_colorlist_item_color_transparent_3",
        };

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

    async _askForPin() {
        try {
            const inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Ingrese PIN de cajero"),
            });

            if (!inputPin) {
                this.notification.add(_t("Operación de PIN cancelada"), {
                    type: "info",
                });
                setTimeout(() => {
                    this._askForPin();
                }, 500);
                return;
            }

            // Verificar el PIN con los empleados disponibles
            const allEmployees = this.pos.data.models["hr.employee"].getAll();
            const hashedPin = Sha1.hash(inputPin);
            const matchedEmployee = allEmployees.find(
                (employee) => employee._pin === hashedPin
            );

            if (matchedEmployee) {
                this.pos.hasLoggedIn = true;
                this.pos.set_cashier(matchedEmployee);
                this.notification.add(_t("Cajero seleccionado: ") + matchedEmployee.name, {
                    type: "success",
                });
            } else {
                this.notification.add(_t("PIN no encontrado"), {
                    type: "warning",
                    title: _t("PIN incorrecto"),
                });
                setTimeout(() => {
                    this._askForPin();
                }, 800);
            }
        } catch (error) {
            console.error("Error al procesar el PIN:", error);
            setTimeout(() => {
                this._askForPin();
            }, 800);
        }
    },

    async addProductToOrder(product) {
        const order = this.pos.get_order();
        const pricelist = order?.pricelist || this.pos.config.pricelist;
        const partner = order?.partner;

        const precioBase = product.lst_price || product.list_price || 0;
        let precioCalculado = product.get_price(pricelist, partner);

        console.log("Producto:", product.display_name || product.name);
        console.log("Precio base:", precioBase);
        console.log("Precio calculado:", precioCalculado);

        const productId = product.id;
        let precioReal = precioCalculado;
        let tarifaItem = null;

        try {
            if (pricelist && pricelist.items) {
                tarifaItem = pricelist.items.find(item =>
                    item.product_id && item.product_id[0] === productId);

                if (tarifaItem && tarifaItem.fixed_price) {
                    precioReal = tarifaItem.fixed_price;
                    console.log("Precio desde regla de tarifa:", precioReal);
                } else if (tarifaItem && tarifaItem.percent_price) {
                    console.log("Porcentaje de tarifa encontrado:", tarifaItem.percent_price);
                    precioReal = precioBase * (1 - tarifaItem.percent_price / 100);
                    console.log("Precio calculado con porcentaje:", precioReal);
                }
            }
        } catch (error) {
            console.log("Error al buscar regla de tarifa:", error);
        }

        const orderLines = order.get_orderlines();
        const existingLine = orderLines.find(line => line.get_product().id === product.id);
        console.log("Líneas del pedido:", orderLines);
        console.log("Línea existente encontrada:", existingLine);

        if (existingLine) {
            const currentQty = existingLine.get_quantity();
            existingLine.set_quantity(currentQty + 1);
            order.select_orderline(existingLine);
            console.log("Incrementada cantidad en línea existente:", currentQty + 1);

            console.log("manual_price:", product.manual_price);
            console.log("existingLine.price_manually_set:", existingLine.price_manually_set);

            if (product.manual_price && !existingLine.price_manually_set) {
                existingLine.price_manually_set = true;
                console.log("📝 Mostrando diálogo para entrada de precio manual");
                const inputPrice = await makeAwaitable(this.dialog, CustomPricePopup, {
                    title: _t("Ingrese precio para") + ` ${product.display_name || product.name}`,
                    startingValue: "",
                });

                if (inputPrice) {
                    const precio = parseFloat(inputPrice);
                    if (!isNaN(precio) && precio > 0) {
                        existingLine.set_unit_price(precio);
                        const porcentajeDescuento = Math.round((1 - (precio / precioBase)) * 100 * 100) / 100;
                        existingLine.set_discount(porcentajeDescuento);
                        this.notification.add(_t("Precio personalizado aplicado"), { type: "success" });
                    } else {
                        existingLine.set_quantity(currentQty);
                        this.notification.add(_t("Precio inválido"), { type: "warning" });
                    }
                } else {
                    existingLine.set_quantity(currentQty);
                    this.notification.add(_t("Operación cancelada"), { type: "info" });
                }
            }
        } else {
            await this.pos.addLineToCurrentOrder({ product_id: product.id }, {});
            const orderLines = order.get_orderlines();
            const lastLine = orderLines[orderLines.length - 1];
            const usarPrecio = Math.min(precioCalculado, precioReal);
            console.log("Precio a usar para visualización:", usarPrecio);
            console.log("Comparando precios:", precioBase, "vs", usarPrecio);

            if (precioBase > usarPrecio && Math.abs(precioBase - usarPrecio) > 0.0001) {
                const porcentajeDescuento = Math.round((1 - (usarPrecio / precioBase)) * 100 * 100) / 100;
                console.log("Aplicando descuento visual:", porcentajeDescuento + "%");
                if (lastLine) {
                    lastLine.set_unit_price(precioBase);
                    lastLine.set_discount(porcentajeDescuento);
                    console.log("Precio base establecido:", precioBase);
                    console.log("Descuento aplicado:", porcentajeDescuento + "%");
                }
            } else if (lastLine) {
                const precioLinea = lastLine.get_unit_price();
                console.log("Precio en línea de pedido:", precioLinea);

                if (precioBase > precioLinea && Math.abs(precioBase - precioLinea) > 0.0001) {
                    const porcentajeDescuento = Math.round((1 - (precioLinea / precioBase)) * 100 * 100) / 100;
                    console.log("Aplicando descuento basado en precio línea:", porcentajeDescuento + "%");
                    lastLine.set_unit_price(precioBase);
                    lastLine.set_discount(porcentajeDescuento);

                    if (product.manual_price) {
                        lastLine.price_manually_set = true;
                        console.log("📝 Mostrando diálogo para entrada de precio manual");
                        const inputPrice = await makeAwaitable(this.dialog, CustomPricePopup, {
                            title: _t("Ingrese precio para") + ` ${product.display_name || product.name}`,
                            startingValue: "",
                        });
                        console.log("💰 Precio ingresado:", inputPrice);

                        if (inputPrice) {
                            const precio = parseFloat(inputPrice);
                            if (!isNaN(precio) && precio > 0) {
                                lastLine.set_unit_price(precio);
                                lastLine.set_discount(porcentajeDescuento);
                                this.pos.get_order().select_orderline(lastLine);
                                this.notification.add(_t("Producto añadido con precio personalizado"), { type: "success" });
                            } else {
                                order.remove_orderline(lastLine);
                                this.notification.add(_t("Precio inválido"), { type: "warning" });
                            }
                        } else {
                            order.remove_orderline(lastLine);
                            this.notification.add(_t("Operación cancelada"), { type: "info" });
                        }
                    }
                }
            }
        }
    },

    get isBasicUser() {
        if (!this.pos.get_cashier) {
            return false;
        }

        const cashier = this.pos.get_cashier();

        if (cashier && cashier._role === 'manager') {
            return false;
        } else if (cashier && cashier._role === 'cashier') {
            return true;
        }
    }
});
