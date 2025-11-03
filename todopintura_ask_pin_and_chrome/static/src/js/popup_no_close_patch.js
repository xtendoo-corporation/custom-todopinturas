/** @odoo-module **/
console.info('[todopintura] popup_no_close_patch.js asset executing');

import { Component } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

// Variable global para controlar cuándo los popups no deben poder cerrarse
window.__TODOPINTURA_BLOCK_POPUP_CLOSE = false;

// Patchear Component para interceptar la tecla ESC en todos los componentes
const originalOnKeydown = Component.prototype.onKeydown;
if (originalOnKeydown) {
    Component.prototype.onKeydown = function(ev) {
        if (window.__TODOPINTURA_BLOCK_POPUP_CLOSE && ev.key === 'Escape') {
            // Verificar si estamos en un popup/dialog relacionado con empleados
            const title = this.props?.title || this.title || '';
            if (title.includes('Cajero') ||
                title.includes('PIN') ||
                title.includes('Seleccionar') ||
                title.includes('Empleado')) {
                console.log('[todopintura] Bloqueando ESC en popup:', title);
                ev.preventDefault();
                ev.stopPropagation();
                return;
            }
        }
        if (originalOnKeydown) {
            return originalOnKeydown.call(this, ev);
        }
    };
}

// Interceptar eventos de teclado globalmente
document.addEventListener('keydown', function(ev) {
    if (window.__TODOPINTURA_BLOCK_POPUP_CLOSE && ev.key === 'Escape') {
        // Buscar si hay algún modal/popup abierto
        const modals = document.querySelectorAll('.modal, .popup, [role="dialog"]');
        for (const modal of modals) {
            const title = modal.querySelector('.modal-title, .popup-title, h1, h2, h3');
            if (title) {
                const titleText = title.textContent || '';
                if (titleText.includes('Cajero') ||
                    titleText.includes('PIN') ||
                    titleText.includes('Seleccionar') ||
                    titleText.includes('Empleado')) {
                    console.log('[todopintura] Bloqueando ESC global en popup:', titleText);
                    ev.preventDefault();
                    ev.stopPropagation();
                    return false;
                }
            }
        }
    }
}, true);

console.info('[todopintura] popup_no_close_patch.js loaded - ESC blocking active');

