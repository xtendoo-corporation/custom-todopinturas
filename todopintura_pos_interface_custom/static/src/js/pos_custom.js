/** @odoo-module **/

// Módulo simple para personalización del POS de Todo Pintura
// Objetivo: Ocultar productos y expandir área del pedido

window.todoPinturaHelpers = {
    // Verificar si estamos en la pantalla principal del POS
    isProductScreen() {
        return document.querySelector('.pos .product-screen') !== null;
    },

    // Aplicar estilos CSS directamente en el head para que funcionen inmediatamente
    injectCustomCSS() {
        // Crear el CSS personalizado
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

            /* Reducir MÁS el contenedor de impuestos y totales */
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

            /* Forzar que el panel izquierdo use flexbox para mejor distribución */
            .pos .product-screen .leftpane {
                display: flex !important;
                flex-direction: column !important;
                justify-content: space-between !important;
                height: 100vh !important;
            }

            /* Hacer que los botones de la parte inferior estén pegados al final */
            .pos .product-screen .actionpad,
            .pos .product-screen .payment-methods {
                margin-top: auto !important;
                margin-bottom: 0px !important;
                padding-bottom: 0px !important;
                min-height: 120px !important;
                max-height: 150px !important;
            }

            /* Eliminar cualquier padding/margin del contenedor principal */
            .pos .product-screen .leftpane {
                padding-bottom: 0px !important;
                margin-bottom: 0px !important;
            }

            /* Eliminar espacios de cualquier contenedor padre */
            .pos .product-screen {
                padding-bottom: 0px !important;
                margin-bottom: 0px !important;
            }

            /* Forzar que no haya espacios en los botones finales */
            .pos .product-screen .actionpad .button,
            .pos .product-screen .payment-methods .button,
            .pos .product-screen .actionpad > *:last-child,
            .pos .product-screen .payment-methods > *:last-child {
                margin-bottom: 0px !important;
                padding-bottom: 5px !important;
            }

            /* FORZAR eliminación completa de espacios inferiores */
            .pos .product-screen,
            .pos .product-screen *,
            .pos .product-screen .leftpane,
            .pos .product-screen .leftpane *,
            .pos .product-screen .actionpad,
            .pos .product-screen .payment-methods,
            body.o_web_client,
            html {
                margin-bottom: 0px !important;
                padding-bottom: 0px !important;
            }

            /* Posicionamiento absoluto para los botones inferiores */
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
            }

            /* Asegurar que el leftpane tenga espacio para los botones absolutos */
            .pos .product-screen .leftpane {
                padding-bottom: 145px !important;
                position: relative !important;
            }
        `;

        // Eliminar CSS anterior si existe
        const existingStyle = document.getElementById('todopintura-pos-custom');
        if (existingStyle) {
            existingStyle.remove();
        }

        // Crear e inyectar el nuevo CSS
        const style = document.createElement('style');
        style.id = 'todopintura-pos-custom';
        style.textContent = customCSS;
        document.head.appendChild(style);
    },

    // Aplicar estilos para ocultar productos y expandir pedido
    applyBasicStyles() {
        if (!this.isProductScreen()) return;

        // OCULTAR completamente el panel de productos (lado derecho)
        const rightPane = document.querySelector('.pos .product-screen .rightpane');
        if (rightPane) {
            rightPane.style.display = 'none';
        }

        // EXPANDIR el panel del pedido para usar TODO el espacio disponible
        const leftPane = document.querySelector('.pos .product-screen .leftpane');
        if (leftPane) {
            leftPane.style.width = '100%';
            leftPane.style.flex = '1';
            leftPane.style.maxWidth = '100%';
        }

        // Inyectar CSS personalizado para alturas
        this.injectCustomCSS();
    }
};

// Aplicar inmediatamente
window.todoPinturaHelpers.injectCustomCSS();

// Aplicar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.todoPinturaHelpers.injectCustomCSS();
    setTimeout(() => {
        window.todoPinturaHelpers.applyBasicStyles();
    }, 500);
});

// Aplicar cuando la página esté completamente cargada
window.addEventListener('load', () => {
    setTimeout(() => {
        window.todoPinturaHelpers.applyBasicStyles();
    }, 1000);
});

// Aplicar más frecuentemente al inicio
setInterval(() => {
    if (window.todoPinturaHelpers.isProductScreen()) {
        window.todoPinturaHelpers.applyBasicStyles();
    }
}, 1000); // Más frecuente para asegurar que se aplique
