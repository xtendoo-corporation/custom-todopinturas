// static/src/js/pos_custom_footer.js
/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();

        console.log("Parche ProductScreen en Odoo 19");

        // Debug más profundo: ver estructura de models y selectedOrderUuid
        console.log("this.pos.selectedOrderUuid:", this.pos.selectedOrderUuid);
        console.log("this.pos.models:", this.pos.models);
        console.log("this.pos.models keys:", this.pos.models ? Object.keys(this.pos.models) : 'no models');

        // Buscar el modelo de órdenes
        if (this.pos.models) {
            for (const [key, value] of Object.entries(this.pos.models)) {
                console.log(`Model ${key}:`, value);
                if (key.toLowerCase().includes('order')) {
                    console.log(`Found order model: ${key}`, value);
                }
            }
        }

        // Inyectamos CSS mejorado con líneas mucho más grandes
        const styleId = "pos-custom-style";
        if (!document.getElementById(styleId)) {
            const style = document.createElement("style");
            style.id = styleId;
            style.textContent = `
                /* Ocultar panel derecho */
                .pos .product-screen .rightpane {
                    display: none !important;
                }

                /* Panel izquierdo a pantalla completa */
                .pos .product-screen .leftpane {
                    width: 100% !important;
                    max-width: 100% !important;
                }

                /* Contenedor de líneas con scroll y más espacio */
                .pos .product-screen .orderlines {
                    font-size: 20px !important;
                    padding: 10px !important;
                }

                /* Líneas de pedido - tamaño aumentado y menos padding vertical */
                .pos .orderline {
                    min-height: 70px !important;
                    padding: 10px 15px !important;
                    font-size: 20px !important;
                    margin-bottom: 8px !important;
                    border: 2px solid #e0e0e0 !important;
                    border-radius: 8px !important;
                    background: #fafafa !important;
                    line-height: 1.4 !important;
                }

                /* Línea seleccionada más visible */
                .pos .orderline.selected {
                    background: #e3f2fd !important;
                    border-color: #2196F3 !important;
                    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3) !important;
                }

                /* Nombre del producto aumentado */
                .pos .orderline .product-name {
                    font-size: 22px !important;
                    font-weight: 700 !important;
                    color: #1a1a1a !important;
                    display: block !important;
                    margin-bottom: 5px !important;
                }

                /* Información adicional */
                .pos .orderline .info,
                .pos .orderline .info-list {
                    font-size: 18px !important;
                    color: #555 !important;
                    display: block !important;
                    margin-top: 3px !important;
                }

                /* Cantidad aumentada */
                .pos .orderline .qty {
                    font-size: 20px !important;
                    font-weight: 600 !important;
                    color: #2196F3 !important;
                }

                /* Precio aumentado */
                .pos .orderline .price,
                .pos .orderline .price-subtotal {
                    font-size: 22px !important;
                    font-weight: bold !important;
                    color: #4CAF50 !important;
                }

                /* Precio unitario */
                .pos .orderline .unit-price {
                    font-size: 18px !important;
                    color: #777 !important;
                }

                /* Descuento */
                .pos .orderline .discount {
                    font-size: 18px !important;
                    font-weight: 600 !important;
                    color: #FF5722 !important;
                }

                /* Mejorar espaciado interno */
                .pos .orderline > * {
                    display: inline-block !important;
                    vertical-align: middle !important;
                }

                /* Hacer el área de scroll más grande */
                .pos .order-scroller {
                    max-height: calc(100vh - 300px) !important;
                }

                /* Total del pedido - tamaño moderado */
                .pos .order-total {
                    font-size: 42px !important;
                    font-weight: bold !important;
                    padding: 12px !important;
                }

                /* TOTALES E IMPUESTOS - Tamaño moderado */
                /* TOTAL - Tamaño más grande */
                .pos .total,
                .pos .total-amount,
                .pos .total-price {
                    font-size: 48px !important;
                    font-weight: 900 !important;
                    color: #2196F3 !important;
                    padding: 12px 8px !important;
                }

                /* Etiquetas de Total, Subtotal e Impuestos - MÁS GRANDES */
                .pos .total .label,
                .pos .order-total .label,
                .pos .subtotal .label,
                .pos .tax .label,
                .pos .summary .label,
                .pos span.label,
                .pos div.label,
                .pos .order-info .label,
                /* Variantes de etiquetas */
                .pos .total-label,
                .pos .subtotal-label,
                .pos .tax-label {
                    font-size: 36px !important;
                    font-weight: 700 !important;
                }

                /* Texto "Total" específico - span con clase total dentro de d-flex */
                .pos .d-flex.justify-content-between span.total,
                .pos .d-flex span.total,
                .pos div.fs-3 span.total,
                .pos span.total {
                    font-size: 40px !important;
                    font-weight: 800 !important;
                }

                /* Todo el contenedor del total más grande */
                .pos .d-flex.justify-content-between.w-100.fs-3 {
                    font-size: 38px !important;
                }

                /* Impuestos - tamaño moderado */
                .pos .tax,
                .pos .taxes,
                .pos .tax-line,
                .pos .tax-info {
                    font-size: 24px !important;
                    font-weight: 600 !important;
                    padding: 8px 5px !important;
                }

                /* Subtotal - tamaño moderado */
                .pos .subtotal,
                .pos .sub-total {
                    font-size: 26px !important;
                    font-weight: 700 !important;
                    padding: 10px 5px !important;
                }

                /* PROTEGER COMPLETAMENTE EL NUMPAD - Solo resetear tamaños */
                .pos .numpad,
                .pos .numpad *,
                .pos .numpad-container,
                .pos .numpad-container *,
                .pos .payment-numpad,
                .pos .payment-numpad *,
                .pos-numpad,
                .pos-numpad *,
                div[class*="numpad"],
                div[class*="numpad"] *,
                div[class*="Numpad"],
                div[class*="Numpad"] *,
                .pos-content .switchpane,
                .pos-content .switchpane *,
                .product-screen .switchpane,
                .product-screen .switchpane * {
                    font-size: revert !important;
                    padding: revert !important;
                    margin: revert !important;
                    line-height: revert !important;
                    min-height: revert !important;
                    /* NO tocar border ni background para mantener colores originales */
                }

                /* Botones del numpad tamaño normal */
                .pos .numpad button,
                .pos .numpad-container button,
                .pos .payment-numpad button,
                .switchpane button {
                    font-size: 16px !important;
                    padding: 8px !important;
                    min-height: auto !important;
                    /* NO tocar background, border, color - mantener estilos originales */
                }

                /* Botones más grandes para mejor UX - EXCEPTO NUMPAD */
                .pos .product-screen button:not(.numpad button):not(.numpad-container button):not(.switchpane button) {
                    font-size: 18px !important;
                    padding: 12px 20px !important;
                    min-height: 50px !important;
                }

                /* ELIMINAR estilos generales que afectan todo */
                /* Ya NO aplicar font-size grande a todo el leftpane */
            `;
            document.head.appendChild(style);
        }
    },

    // Getter temporal para debug
    get currentPartner() {
        try {
            console.log("=== DEBUG currentPartner ===");
            console.log("selectedOrderUuid:", this.pos.selectedOrderUuid);
            console.log("models:", this.pos.models);

            // Intentar encontrar la orden actual en los modelos
            if (this.pos.models && this.pos.selectedOrderUuid) {
                // Buscar en diferentes lugares posibles
                const orderModels = [
                    this.pos.models['pos.order'],
                    this.pos.models.order,
                    this.pos.models.Order,
                    this.pos.models['pos_order']
                ];

                for (const orderModel of orderModels) {
                    if (orderModel) {
                        console.log("Found order model:", orderModel);
                        // Intentar obtener la orden actual
                        const currentOrder = orderModel.get ?
                            orderModel.get(this.pos.selectedOrderUuid) :
                            orderModel[this.pos.selectedOrderUuid];

                        if (currentOrder) {
                            console.log("Current order found:", currentOrder);
                            console.log("Order keys:", Object.keys(currentOrder));

                            // Buscar el partner
                            const partner = currentOrder.partner ||
                                          currentOrder.get_partner?.() ||
                                          currentOrder.partner_id;

                            if (partner) {
                                console.log("Partner found:", partner);
                                return partner;
                            }
                        }
                    }
                }
            }

            console.log("No partner found");
            return null;
        } catch (error) {
            console.error('Error en currentPartner:', error);
            return null;
        }
    },
});
