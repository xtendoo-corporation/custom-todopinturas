/** @odoo-module **/

// Módulo simple para personalización del POS de Todo Pintura
// Solo ampliar líneas del pedido y ocultar productos

window.todoPinturaHelpers = {
    // Verificar si estamos en la pantalla principal del POS
    isProductScreen() {
        return document.querySelector('.pos .product-screen') !== null;
    },

    // Aplicar estilos básicos
    applyBasicStyles() {
        if (!this.isProductScreen()) return;

        // Ocultar panel de productos
        const rightPane = document.querySelector('.pos .product-screen .rightpane');
        if (rightPane) {
            rightPane.style.display = 'none';
        }

        // Expandir panel del pedido
        const leftPane = document.querySelector('.pos .product-screen .leftpane');
        if (leftPane) {
            leftPane.style.width = '100%';
            leftPane.style.flex = '1';
        }

        // Ampliar área del pedido
        const orderSummary = document.querySelector('.pos .product-screen .order-summary');
        if (orderSummary) {
            orderSummary.style.minHeight = '75vh';
            orderSummary.style.flex = '1';
        }

        // Ampliar las líneas del pedido
        const orderlines = document.querySelectorAll('.pos .product-screen .orderline');
        orderlines.forEach(line => {
            line.style.minHeight = '85px';
            line.style.padding = '25px 15px';
            line.style.fontSize = '18px';
            line.style.marginBottom = '8px';
        });

        // Ampliar el área de scroll
        const orderScroller = document.querySelector('.pos .product-screen .order-scroller');
        if (orderScroller) {
            orderScroller.style.flex = '1';
            orderScroller.style.minHeight = '65vh';
        }

        // Ampliar botones de pago
        const paymentMethods = document.querySelectorAll('.pos .product-screen .payment-method');
        paymentMethods.forEach(btn => {
            btn.style.padding = '30px';
            btn.style.fontSize = '20px';
            btn.style.minHeight = '100px';
        });

        // Ampliar el total
        const orderTotal = document.querySelector('.pos .product-screen .order-total');
        if (orderTotal) {
            orderTotal.style.fontSize = '38px';
            orderTotal.style.padding = '30px';
            orderTotal.style.margin = '25px 0';
        }
    }
};

// Aplicar cuando la página esté lista
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        window.todoPinturaHelpers.applyBasicStyles();
    }, 1000);
});

// Aplicar cuando cambie la página
window.addEventListener('load', () => {
    setTimeout(() => {
        window.todoPinturaHelpers.applyBasicStyles();
    }, 2000);
});

// Aplicar periódicamente (solo si estamos en la pantalla correcta)
setInterval(() => {
    if (window.todoPinturaHelpers.isProductScreen()) {
        window.todoPinturaHelpers.applyBasicStyles();
    }
}, 5000);
