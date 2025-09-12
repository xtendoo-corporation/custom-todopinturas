/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { useEffect } from "@odoo/owl";

// Módulo para personalización del POS de Todo Pintura
// Objetivo: Ocultar productos y expandir área del pedido SOLO para usuarios básicos

// Patch del Navbar para integrar con la lógica existente
patch(Navbar.prototype, {
    setup() {
        super.setup?.();

        // Guardar referencia original si existe
        const originalUpdateIsBasicUser = this.updateIsBasicUser;

        this.updateIsBasicUser = () => {
            console.log('=== DEBUGGING USUARIO BÁSICO ===');
            console.log('POS config:', this.pos.config);
            console.log('basic_employee_ids:', this.pos.config.basic_employee_ids);

            // Ejecutar lógica original primero
            if (originalUpdateIsBasicUser) {
                console.log('Ejecutando lógica original de updateIsBasicUser');
                originalUpdateIsBasicUser.call(this);
            } else {
                console.log('No existe lógica original, creando nueva');
                // Crear lógica si no existe
                const basicIds = (this.pos.config.basic_employee_ids || []).map(e => e.id || e);
                const cashier = this.pos.get_cashier();
                console.log('basicIds:', basicIds);
                console.log('cashier:', cashier);
                console.log('cashier.id:', cashier?.id);
                this.isBasicUser = cashier && basicIds.includes(cashier.id);
            }

            console.log('Resultado final isBasicUser:', this.isBasicUser);
            console.log('=== FIN DEBUGGING ===');

            // Aplicar/quitar estilos basado en el tipo de usuario
            this.applyInterfaceCustomization();
        };

        // Nueva función para manejar la personalización de interfaz
        this.applyInterfaceCustomization = () => {
            console.log('Aplicando personalización - Usuario básico:', this.isBasicUser);

            if (this.isBasicUser) {
                console.log('Usuario básico detectado - aplicando personalización de interfaz');
                this.injectBasicUserCSS();
                this.hideProductPanel();
            } else {
                console.log('Usuario con permisos completos - manteniendo interfaz estándar');
                this.removeBasicUserCSS();
                this.showProductPanel();
            }
        };

        // Función para inyectar CSS de usuarios básicos
        this.injectBasicUserCSS = () => {
            // Eliminar CSS anterior si existe
            const existingStyle = document.getElementById('todopintura-pos-custom');
            if (existingStyle) {
                existingStyle.remove();
            }

            const customCSS = `
                /* Aumentar un poco la altura del contenedor de líneas */
                .pos .product-screen .order-widget {
                    max-height: 40vh !important;
                    height: auto !important;
                    overflow-y: auto !important;
                }

                .pos .product-screen .order-summary {
                    max-height: 35vh !important;
                    height: auto !important;
                    overflow-y: auto !important;
                }

                .pos .product-screen .order-scroller {
                    max-height: 30vh !important;
                    height: auto !important;
                    overflow-y: auto !important;
                }

                .pos .product-screen .orderlines {
                    max-height: 30vh !important;
                    height: auto !important;
                    overflow-y: auto !important;
                }

                /* Reducir el contenedor de impuestos y totales */
                .pos .product-screen .summary,
                .pos .product-screen .order-summary-line,
                .pos .product-screen .summary-line,
                .pos .product-screen .total,
                .pos .product-screen .order-total-container,
                .pos .product-screen .payment-summary,
                .pos .product-screen [class*="summary"],
                .pos .product-screen [class*="total"]:not(.orderline) {
                    max-height: 10vh !important;
                    height: auto !important;
                    padding: 6px 10px !important;
                    margin: 3px 0 !important;
                    font-size: 20px !important;
                    font-weight: 600 !important;
                    line-height: 1.3 !important;
                }

                /* Total más compacto pero con letra más grande */
                .pos .product-screen .order-total {
                    max-height: 60px !important;
                    padding: 8px 12px !important;
                    margin: 4px 0 !important;
                    font-size: 26px !important;
                    font-weight: bold !important;
                }

                /* Asegurar que los números sean más legibles */
                .pos .product-screen .summary .value,
                .pos .product-screen .total .value,
                .pos .product-screen [class*="summary"] .value,
                .pos .product-screen [class*="total"] .value {
                    font-size: 22px !important;
                    font-weight: 700 !important;
                }

                /* Panel izquierdo con flexbox */
                .pos .product-screen .leftpane {
                    display: flex !important;
                    flex-direction: column !important;
                    justify-content: space-between !important;
                    height: 100vh !important;
                    width: 100% !important;
                    flex: 1 !important;
                    max-width: 100% !important;
                }

                /* Posicionamiento de botones inferiores */
                .pos .product-screen .actionpad,
                .pos .product-screen .payment-methods {
                    position: absolute !important;
                    bottom: 45px !important;
                    left: 0px !important;
                    right: 0px !important;
                    margin: 0px !important;
                    padding: 5px !important;
                    min-height: 120px !important;
                    max-height: 150px !important;
                    background: inherit !important;
                    overflow: hidden !important;
                }

                /* Reducir espacio específico del actionpad */
                .pos .product-screen .actionpad.d-flex.flex-column.gap-2 {
                    min-height: 100px !important;
                    max-height: 120px !important;
                    padding: 8px !important;
                    gap: 4px !important;
                    margin-top: 20px !important;
                }

                /* Espacio para botones absolutos */
                .pos .product-screen .leftpane {
                    padding-bottom: 145px !important;
                    position: relative !important;
                }

                /* Ocultar panel de productos para usuarios básicos */
                .pos .product-screen .rightpane {
                    display: none !important;
                }
            `;

            const style = document.createElement('style');
            style.id = 'todopintura-pos-custom';
            style.textContent = customCSS;
            document.head.appendChild(style);
        };

        // Función para remover CSS de usuarios básicos
        this.removeBasicUserCSS = () => {
            const existingStyle = document.getElementById('todopintura-pos-custom');
            if (existingStyle) {
                existingStyle.remove();
            }
        };

        // Función para ocultar panel de productos
        this.hideProductPanel = () => {
            console.log('🔸 EJECUTANDO hideProductPanel()');
            setTimeout(() => {
                const rightPane = document.querySelector('.pos .product-screen .rightpane');
                const leftPane = document.querySelector('.pos .product-screen .leftpane');

                console.log('rightPane encontrado:', !!rightPane);
                console.log('leftPane encontrado:', !!leftPane);

                if (rightPane) {
                    rightPane.style.display = 'none';
                    console.log('✅ Panel de productos OCULTADO');
                }

                if (leftPane) {
                    leftPane.style.width = '100%';
                    leftPane.style.flex = '1';
                    leftPane.style.maxWidth = '100%';
                    console.log('✅ Panel izquierdo EXPANDIDO');
                }
            }, 100);
        };

        // Función para mostrar panel de productos
        this.showProductPanel = () => {
            console.log('🔹 EJECUTANDO showProductPanel()');
            setTimeout(() => {
                const rightPane = document.querySelector('.pos .product-screen .rightpane');
                const leftPane = document.querySelector('.pos .product-screen .leftpane');

                console.log('rightPane encontrado:', !!rightPane);
                console.log('leftPane encontrado:', !!leftPane);

                if (rightPane) {
                    // FORZAR la visualización con !important para sobrescribir el CSS
                    rightPane.style.setProperty('display', 'block', 'important');
                    console.log('✅ Panel de productos MOSTRADO con !important');
                    console.log('Display actual del rightPane:', rightPane.style.display);
                }

                if (leftPane) {
                    // Restaurar estilos también con !important para asegurar que se apliquen
                    leftPane.style.setProperty('width', 'auto', 'important');
                    leftPane.style.setProperty('flex', 'initial', 'important');
                    leftPane.style.setProperty('max-width', 'none', 'important');
                    console.log('✅ Panel izquierdo RESTAURADO con !important');
                    console.log('Estilos actuales del leftPane:', {
                        width: leftPane.style.width,
                        flex: leftPane.style.flex,
                        maxWidth: leftPane.style.maxWidth
                    });
                }
            }, 100);
        };

        // Ejecutar al inicializar
        this.updateIsBasicUser();

        // Reaccionar a cambios de cajero
        useEffect(
            () => {
                this.updateIsBasicUser();
            },
            () => [this.pos.get_cashier?.() && this.pos.get_cashier().id]
        );
    },
});
