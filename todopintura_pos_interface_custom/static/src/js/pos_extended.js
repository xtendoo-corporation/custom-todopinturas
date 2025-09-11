/** @odoo-module **/

// Módulo simplificado para Todo Pintura POS
// Enfoque unificado: todo el pedido en un solo contenedor

window.todoPinturaExtended = {
    // Verificar si estamos en la pantalla principal del POS
    isProductScreen() {
        return document.querySelector('.pos .product-screen') !== null;
    },

    // CREAR un contenedor unificado para todo el pedido
    createUnifiedOrderArea() {
        if (!this.isProductScreen()) return;

        // Buscar el contenedor principal
        const leftPane = document.querySelector('.pos .product-screen .leftpane');
        if (!leftPane) return;

        // Verificar si ya existe nuestro contenedor unificado
        if (document.querySelector('#unified-order-container')) return;

        // Ocultar el contenedor original de Odoo
        const originalOrderSummary = document.querySelector('.pos .product-screen .order-summary');
        if (originalOrderSummary) {
            originalOrderSummary.style.display = 'none';
        }

        // Forzar estilos del leftPane para tener posicionamiento relativo
        leftPane.style.cssText = `
            position: relative !important;
            width: 100% !important;
            height: 100vh !important;
            display: block !important;
        `;

        // Crear contenedor unificado con posición absoluta
        const unifiedContainer = document.createElement('div');
        unifiedContainer.id = 'unified-order-container';
        unifiedContainer.style.cssText = `
            position: absolute !important;
            top: 20px !important;
            left: 10px !important;
            right: 10px !important;
            height: 100px !important;
            width: calc(100% - 20px) !important;
            display: flex !important;
            flex-direction: column !important;
            background-color: #ffffff !important;
            border: 3px solid #ff0000 !important;
            border-radius: 10px !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            z-index: 99999 !important;
        `;

        // Crear área de líneas del pedido (parte superior)
        const orderLinesArea = document.createElement('div');
        orderLinesArea.id = 'order-lines-area';
        orderLinesArea.style.cssText = `
            flex: 1 !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            padding: 2px !important;
            background-color: #f8f9fa !important;
            border-bottom: 1px solid #dee2e6 !important;
            max-height: 50px !important;
        `;

        // Crear área de totales (parte inferior fija)
        const totalsArea = document.createElement('div');
        totalsArea.id = 'totals-area';
        totalsArea.style.cssText = `
            flex: 0 0 auto !important;
            height: 40px !important;
            padding: 2px !important;
            background-color: #ffffff !important;
            border-top: 1px solid #28a745 !important;
            font-size: 9px !important;
        `;

        // Contenido inicial del área de totales
        totalsArea.innerHTML = `
            <div style="font-size: 9px; font-weight: bold; color: #28a745; margin-bottom: 1px; text-align: center;">
                RESUMEN
            </div>
            <div style="display: flex; justify-content: space-between; margin: 1px 0; font-size: 8px;">
                <span>Subtotal:</span>
                <span id="subtotal-amount" style="font-weight: bold;">€0.00</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 1px 0; font-size: 8px;">
                <span>Impuestos:</span>
                <span id="tax-amount" style="font-weight: bold;">€0.00</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 1px 0; padding: 1px; background-color: #e8f5e8; border-radius: 2px; font-size: 9px; font-weight: bold; border: 1px solid #28a745;">
                <span>TOTAL:</span>
                <span id="total-amount" style="color: #28a745;">€0.00</span>
            </div>
        `;

        // Ensamblar el contenedor
        unifiedContainer.appendChild(orderLinesArea);
        unifiedContainer.appendChild(totalsArea);

        // Agregar al leftPane
        leftPane.appendChild(unifiedContainer);

        console.log('Contenedor unificado de pedido creado');
    },

    // MOVER las líneas del pedido al área unificada
    moveOrderLinesToUnified() {
        if (!this.isProductScreen()) return;

        const orderLinesArea = document.getElementById('order-lines-area');
        if (!orderLinesArea) return;

        // Buscar las líneas del pedido originales
        const originalOrderlines = document.querySelectorAll('.pos .product-screen .orderline');

        originalOrderlines.forEach(line => {
            // Clonar la línea y mejorar su estilo
            const clonedLine = line.cloneNode(true);

            // Aplicar estilos mejorados a la línea clonada
            clonedLine.style.cssText = `
                display: block !important;
                min-height: 25px !important;
                padding: 5px !important;
                margin-bottom: 3px !important;
                background-color: #ffffff !important;
                border: 1px solid #dee2e6 !important;
                border-radius: 3px !important;
                font-size: 12px !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
                visibility: visible !important;
                opacity: 1 !important;
            `;

            // Mejorar el texto del producto en la línea clonada
            const productName = clonedLine.querySelector('.product-name');
            if (productName) {
                productName.style.cssText = `
                    font-size: 13px !important;
                    font-weight: bold !important;
                    color: #2c3e50 !important;
                    margin-bottom: 2px !important;
                `;
            }

            // Mover la línea clonada al área unificada
            orderLinesArea.appendChild(clonedLine);

            // Ocultar la línea original
            line.style.display = 'none';
        });
    },

    // ACTUALIZAR los totales automáticamente
    updateTotals() {
        if (!this.isProductScreen()) return;

        // Buscar los elementos de display
        const subtotalElement = document.getElementById('subtotal-amount');
        const taxElement = document.getElementById('tax-amount');
        const totalElement = document.getElementById('total-amount');

        if (!subtotalElement || !taxElement || !totalElement) return;

        // Calcular totales desde las líneas del pedido visibles
        let subtotal = 0;
        let total = 0;

        const orderLines = document.querySelectorAll('#order-lines-area .orderline');
        orderLines.forEach(line => {
            const priceElement = line.querySelector('.price');
            if (priceElement) {
                const priceText = priceElement.textContent.replace(/[€,]/g, '');
                const price = parseFloat(priceText) || 0;
                subtotal += price;
            }
        });

        // Calcular impuestos (estimado como 21% para España)
        const tax = subtotal * 0.21;
        total = subtotal + tax;

        // Actualizar los displays
        subtotalElement.textContent = `€${subtotal.toFixed(2)}`;
        taxElement.textContent = `€${tax.toFixed(2)}`;
        totalElement.textContent = `€${total.toFixed(2)}`;
    },

    // APLICAR estilos de barra de scroll personalizada
    applyScrollStyles() {
        if (document.getElementById('unified-scroll-styles')) return;

        const scrollStyle = document.createElement('style');
        scrollStyle.id = 'unified-scroll-styles';
        scrollStyle.textContent = `
            /* Forzar el contenedor a tamaño específico usando position absolute */
            #unified-order-container {
                position: absolute !important;
                top: 20px !important;
                left: 10px !important;
                right: 10px !important;
                height: 100px !important;
                width: calc(100% - 20px) !important;
                display: flex !important;
                flex-direction: column !important;
                background-color: #ffffff !important;
                border: 3px solid #ff0000 !important;
                border-radius: 10px !important;
                box-sizing: border-box !important;
                overflow: hidden !important;
                z-index: 99999 !important;
            }

            /* Estilos para la barra de scroll */
            #order-lines-area::-webkit-scrollbar {
                width: 12px;
            }

            #order-lines-area::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 6px;
            }

            #order-lines-area::-webkit-scrollbar-thumb {
                background: linear-gradient(180deg, #007bff 0%, #0056b3 100%);
                border-radius: 6px;
                border: 1px solid #004085;
            }

            #order-lines-area::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(180deg, #0056b3 0%, #004085 100%);
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
        `;
        document.head.appendChild(scrollStyle);
    },

    // OCULTAR el panel de productos
    hideProductPanel() {
        const rightPane = document.querySelector('.pos .product-screen .rightpane');
        if (rightPane) {
            rightPane.style.display = 'none';
        }

        const leftPane = document.querySelector('.pos .product-screen .leftpane');
        if (leftPane) {
            leftPane.style.width = '100%';
        }
    },

    // AMPLIAR botones de acción
    enhanceActionButtons() {
        const buttons = document.querySelectorAll('.pos .product-screen .actionpad .button, .pos .product-screen .payment-method');
        buttons.forEach(btn => {
            btn.style.cssText = `
                min-height: 65px !important;
                padding: 18px 25px !important;
                font-size: 16px !important;
                font-weight: bold !important;
                margin: 8px 5px !important;
                border-radius: 8px !important;
            `;
        });
    },

    // INICIALIZAR todo
    init() {
        if (!this.isProductScreen()) return;

        this.hideProductPanel();
        this.createUnifiedOrderArea();
        this.applyScrollStyles();
        this.enhanceActionButtons();

        // Pequeño delay para que se carguen las líneas del pedido
        setTimeout(() => {
            this.moveOrderLinesToUnified();
            this.updateTotals();
        }, 500);

        console.log('Todo Pintura POS: Sistema unificado inicializado');
    }
};

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        window.todoPinturaExtended.init();
    }, 1000);
});

window.addEventListener('load', () => {
    setTimeout(() => {
        window.todoPinturaExtended.init();
    }, 2000);
});

// Actualizar periódicamente
setInterval(() => {
    if (window.todoPinturaExtended && window.todoPinturaExtended.isProductScreen()) {
        window.todoPinturaExtended.moveOrderLinesToUnified();
        window.todoPinturaExtended.updateTotals();
        window.todoPinturaExtended.enhanceActionButtons();
    }
}, 3000);

// Observer para cambios en el DOM
const observer = new MutationObserver(() => {
    if (window.todoPinturaExtended && window.todoPinturaExtended.isProductScreen()) {
        setTimeout(() => {
            window.todoPinturaExtended.moveOrderLinesToUnified();
            window.todoPinturaExtended.updateTotals();
        }, 200);
    }
});

setTimeout(() => {
    const posContainer = document.querySelector('.pos');
    if (posContainer) {
        observer.observe(posContainer, {
            childList: true,
            subtree: true
        });
    }
}, 2000);
