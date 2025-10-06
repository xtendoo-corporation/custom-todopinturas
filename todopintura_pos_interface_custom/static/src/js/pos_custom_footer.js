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
                    font-size: 38px !important;
                    padding: 10px !important;
                }

                /* Líneas de pedido MUCHO más grandes */
                .pos .orderline {
                    min-height: 90px !important;
                    padding: 20px 15px !important;
                    font-size: 32px !important;
                    margin-bottom: 8px !important;
                    border: 2px solid #e0e0e0 !important;
                    border-radius: 8px !important;
                    background: #fafafa !important;
                    line-height: 1.6 !important;
                }

                /* Línea seleccionada más visible */
                .pos .orderline.selected {
                    background: #e3f2fd !important;
                    border-color: #2196F3 !important;
                    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3) !important;
                }

                /* Nombre del producto más grande y destacado */
                .pos .orderline .product-name {
                    font-size: 30px !important;
                    font-weight: 700 !important;
                    color: #1a1a1a !important;
                    display: block !important;
                    margin-bottom: 8px !important;
                }

                /* Información adicional (cantidad, precio unitario) */
                .pos .orderline .info,
                .pos .orderline .info-list {
                    font-size: 24px !important;
                    color: #555 !important;
                    display: block !important;
                    margin-top: 5px !important;
                }

                /* Cantidad más visible */
                .pos .orderline .qty {
                    font-size: 28px !important;
                    font-weight: 600 !important;
                    color: #2196F3 !important;
                }

                /* Precio más grande y destacado */
                .pos .orderline .price,
                .pos .orderline .price-subtotal {
                    font-size: 32px !important;
                    font-weight: bold !important;
                    color: #4CAF50 !important;
                }

                /* Precio unitario */
                .pos .orderline .unit-price {
                    font-size: 24px !important;
                    color: #777 !important;
                }

                /* Descuento si existe */
                .pos .orderline .discount {
                    font-size: 24px !important;
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

                /* Total del pedido más visible */
                .pos .order-total {
                    font-size: 32px !important;
                    font-weight: bold !important;
                    padding: 15px !important;
                }

                /* Botones más grandes para mejor UX */
                .pos .product-screen button {
                    font-size: 18px !important;
                    padding: 12px 20px !important;
                    min-height: 50px !important;
                }
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
