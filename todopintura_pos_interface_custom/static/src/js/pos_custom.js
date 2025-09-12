/** @odoo-module **/

// Módulo simple para personalización del POS de Todo Pintura
// Objetivo: Ocultar productos y expandir área del pedido

window.todoPinturaHelpers = {
    // Verificar si estamos en la pantalla principal del POS
    isProductScreen() {
        return document.querySelector('.pos .product-screen') !== null;
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
    }
};

// Aplicar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        window.todoPinturaHelpers.applyBasicStyles();
    }, 1000);
});

// Aplicar cuando la página esté completamente cargada
window.addEventListener('load', () => {
    setTimeout(() => {
        window.todoPinturaHelpers.applyBasicStyles();
    }, 2000);
});

// Aplicar periódicamente para mantener los cambios
setInterval(() => {
    if (window.todoPinturaHelpers.isProductScreen()) {
        window.todoPinturaHelpers.applyBasicStyles();
    }
}, 3000);
