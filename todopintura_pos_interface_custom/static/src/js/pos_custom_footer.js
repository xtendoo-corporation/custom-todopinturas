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

        // Inyectar el panel de información del cliente después de que el componente se monte
        setTimeout(() => {
            this.injectCustomerInfoPanel();
        }, 100);

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

                /* ========== PANEL DE INFORMACIÓN DEL CLIENTE ========== */

                /* Contenedor .pads debe permitir el layout lado a lado */
                .pos .product-screen .leftpane .pads {
                    display: flex !important;
                    flex-wrap: wrap !important;
                    gap: 10px !important;
                }

                /* Panel de información del cliente - Mitad izquierda */
                .pos .customer-info-panel {
                    width: calc(50% - 5px) !important;
                    padding: 15px !important;
                    background: #f8f9fa !important;
                    border: 2px solid #dee2e6 !important;
                    border-radius: 8px !important;
                    min-height: 400px !important;
                    box-sizing: border-box !important;
                    order: 1 !important;
                }

                /* Subpads (numpad + botones) - Mitad derecha */
                .pos .product-screen .leftpane .pads .subpads {
                    width: calc(50% - 5px) !important;
                    box-sizing: border-box !important;
                    order: 2 !important;
                    display: flex !important;
                    flex-direction: column !important;
                    min-height: 400px !important;
                }

                /* Numpad mantiene su layout original pero ocupa más espacio */
                .pos .product-screen .leftpane .pads .subpads .numpad {
                    flex-grow: 1 !important;
                    /* NO cambiar su display, mantener el grid original */
                }

                /* ActionpadWidget (botones de pago) al final */
                .pos .product-screen .leftpane .pads .subpads > *:last-child {
                    margin-top: auto !important;
                }

                /* Control buttons arriba de todo */
                .pos .product-screen .leftpane .pads .control-buttons {
                    width: 100% !important;
                    order: 0 !important;
                }

                /* Header del panel de cliente */
                .pos .customer-info-header {
                    font-size: 24px !important;
                    font-weight: 700 !important;
                    color: #2196F3 !important;
                    margin-bottom: 15px !important;
                    padding-bottom: 10px !important;
                    border-bottom: 2px solid #2196F3 !important;
                }

                .pos .customer-info-header i {
                    margin-right: 10px !important;
                }

                /* Contenido del panel */
                .pos .customer-info-content {
                    font-size: 18px !important;
                }

                /* Cada detalle del cliente */
                .pos .customer-detail {
                    padding: 8px 0 !important;
                    font-size: 18px !important;
                    line-height: 1.6 !important;
                    border-bottom: 1px solid #e0e0e0 !important;
                }

                .pos .customer-detail i {
                    width: 25px !important;
                    color: #666 !important;
                    margin-right: 10px !important;
                }

                /* Nombre del cliente destacado */
                .pos .customer-name {
                    font-size: 22px !important;
                    color: #1a1a1a !important;
                    display: block !important;
                    margin-bottom: 10px !important;
                }

                /* Mensaje cuando no hay cliente */
                .pos .no-customer {
                    text-align: center !important;
                    padding: 40px 20px !important;
                    color: #999 !important;
                }

                .pos .no-customer i {
                    color: #ccc !important;
                    margin-bottom: 20px !important;
                }

                .pos .no-customer p {
                    font-size: 20px !important;
                    margin: 20px 0 !important;
                }

                /* Switchpane (Numpad + Botones) - Mitad derecha */
                .pos .product-screen .switchpane {
                    width: 48% !important;
                    float: right !important;
                    box-sizing: border-box !important;
                }

                /* Clearfix para los floats */
                .pos .product-screen .leftpane::after {
                    content: "" !important;
                    display: table !important;
                    clear: both !important;
                }

                /* ELIMINAR estilos generales que afectan todo */
                /* Ya NO aplicar font-size grande a todo el leftpane */
            `;
            document.head.appendChild(style);
        }
    },

    injectCustomerInfoPanel() {
        // Evitar inyección duplicada
        if (document.getElementById('customer-info-panel-injected')) {
            return;
        }

        // Buscar el contenedor .pads (donde están los botones y numpad)
        const padsElement = document.querySelector('.pos .product-screen .leftpane .pads');

        if (padsElement) {
            // Crear el panel de información del cliente
            const customerPanel = document.createElement('div');
            customerPanel.id = 'customer-info-panel-injected';
            customerPanel.className = 'customer-info-panel';

            // Insertar el panel DENTRO de .pads, al principio (antes de .control-buttons)
            padsElement.insertBefore(customerPanel, padsElement.firstChild);

            console.log('Panel de cliente inyectado correctamente dentro de .pads');

            // Actualizar el contenido del panel
            this.updateCustomerInfo();

            // Observar cambios en la orden para actualizar el panel
            this.setupOrderObserver();
        } else {
            console.warn('No se encontró .pads para inyectar el panel de cliente');
        }
    },

    setupOrderObserver() {
        // Actualizar el panel cuando cambie la orden seleccionada
        if (this.env && this.env.services && this.env.services.pos) {
            // Usar un pequeño intervalo para detectar cambios
            setInterval(() => {
                this.updateCustomerInfo();
            }, 1000);
        }
    },

    updateCustomerInfo() {
        const customerPanel = document.getElementById('customer-info-panel-injected');
        if (!customerPanel) return;

        // Obtener la orden actual
        let order = null;
        let partner = null;

        try {
            // Intentar obtener la orden
            if (this.pos && typeof this.pos.get_order === 'function') {
                order = this.pos.get_order();
            } else if (this.pos && this.pos.selectedOrder) {
                order = this.pos.selectedOrder;
            }

            // Obtener el partner de la orden
            if (order && order.partner_id) {
                // En Odoo 19, partner_id es un Proxy object con sus propiedades
                partner = order.partner_id;
                console.log('✅ Partner encontrado:', partner.name || partner);
            }
        } catch (error) {
            console.error('❌ Error obteniendo orden/partner:', error);
        }

        if (partner && partner.name) {
            customerPanel.innerHTML = `
                <div class="customer-info-header">
                    <i class="fa fa-user"></i>
                    <span>Información del Cliente</span>
                </div>
                <div class="customer-info-content">
                    <div class="customer-detail">
                        <strong class="customer-name">${this.escapeHtml(partner.name || '')}</strong>
                    </div>
                    ${partner.street ? `
                        <div class="customer-detail">
                            <i class="fa fa-map-marker"></i>
                            <span>${this.escapeHtml(partner.street)}${partner.street2 ? ', ' + this.escapeHtml(partner.street2) : ''}</span>
                        </div>
                    ` : ''}
                    ${partner.zip || partner.city ? `
                        <div class="customer-detail">
                            <i class="fa fa-building"></i>
                            <span>${this.escapeHtml(partner.zip || '')} ${this.escapeHtml(partner.city || '')}</span>
                        </div>
                    ` : ''}
                    ${partner.phone ? `
                        <div class="customer-detail">
                            <i class="fa fa-phone"></i>
                            <span>${this.escapeHtml(partner.phone)}</span>
                        </div>
                    ` : ''}
                    ${partner.mobile ? `
                        <div class="customer-detail">
                            <i class="fa fa-mobile"></i>
                            <span>${this.escapeHtml(partner.mobile)}</span>
                        </div>
                    ` : ''}
                    ${partner.email ? `
                        <div class="customer-detail">
                            <i class="fa fa-envelope"></i>
                            <span>${this.escapeHtml(partner.email)}</span>
                        </div>
                    ` : ''}
                    ${partner.vat ? `
                        <div class="customer-detail">
                            <i class="fa fa-id-card"></i>
                            <span>NIF/CIF: ${this.escapeHtml(partner.vat)}</span>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            customerPanel.innerHTML = `
                <div class="customer-info-header">
                    <i class="fa fa-user"></i>
                    <span>Información del Cliente</span>
                </div>
                <div class="customer-info-content">
                    <div class="no-customer">
                        <i class="fa fa-user-times fa-3x"></i>
                        <p>No hay cliente seleccionado</p>
                    </div>
                </div>
            `;
        }
    },

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text ? text.replace(/[&<>"']/g, m => map[m]) : '';
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
