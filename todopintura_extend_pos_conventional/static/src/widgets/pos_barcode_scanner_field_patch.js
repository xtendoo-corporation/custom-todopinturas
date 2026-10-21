/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { barcodeService } from "@barcodes/barcode_service";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { PosConventionalBarcodeScannerField } from "@pos_conventional_barcode_scanner/js/pos_conventional_barcode_scanner_field";

const BARCODE_ONLY_BODY_CLASS = "o_pos_barcode_only_lines";
const EDITABLE_SELECTOR = 'input, textarea, [contenteditable="true"]';
const MIN_BARCODE_LENGTH = 3;
// Un lector teclea mucho más rápido que una persona.
const SCANNER_MAX_KEY_GAP = 80; // ms entre teclas para sospechar de un lector
const SCANNER_ACTIVE_KEY_GAP = 250; // ms tolerados una vez confirmada la ráfaga
const SCANNER_FLUSH_DELAY = 250; // ms sin teclas para dar por terminada la ráfaga

const cleanBarcode = (barcode) => barcodeService.cleanBarcode(barcode);

patch(PosConventionalBarcodeScannerField.prototype, {
    setup() {
        super.setup(...arguments);
        // Sin el check "Puede buscar/escribir productos en TPV" se oculta el enlace
        // "Añadir una línea": las líneas solo se crean escaneando códigos de barras.
        // La clase va en <body> porque OWL repinta (y pisa) las clases de los campos.
        onMounted(() => this._applyBarcodeOnlyLines());
        onPatched(() => this._applyBarcodeOnlyLines());
        onWillUnmount(() => document.body.classList.remove(BARCODE_ONLY_BODY_CLASS));
    },

    _applyBarcodeOnlyLines() {
        const data = this.props.record?.data;
        if (!data || !("can_manual_product_entry" in data)) {
            return;
        }
        document.body.classList.toggle(BARCODE_ONLY_BODY_CLASS, !data.can_manual_product_entry);
    },

    /**
     * Sustituye la captura original, que solo admitía códigos numéricos: un
     * código con letras se dejaba escribir en el campo con el foco. Aquí se
     * detecta el lector por velocidad de tecleo (una persona no teclea tan
     * rápido), con cualquier carácter imprimible.
     * Las primeras teclas se escriben con normalidad; al confirmarse la ráfaga
     * se restaura el valor del campo y el resto de teclas no llega a escribirse.
     */
    _handleKeydownCapture(event) {
        const target = event.target;
        if (
            !(target instanceof HTMLElement) ||
            !this.formElement?.contains(target) ||
            !target.matches(EDITABLE_SELECTOR) ||
            !event.key ||
            event.ctrlKey ||
            event.altKey ||
            event.metaKey ||
            event.repeat
        ) {
            return;
        }
        const burst = this._burst;
        if (/^(Enter|Tab)$/.test(event.key)) {
            if (burst?.active && burst.target === target) {
                // El Enter/Tab final del lector no debe llegar al campo (en una
                // celda de línea elige el autocompletado y añade una fila vacía).
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                this._finishBurst();
            } else {
                this._clearBurst();
            }
            return;
        }
        if (event.key.length !== 1) {
            return; // Shift, flechas...
        }

        // timeStamp = instante real de la tecla, no el de proceso del manejador
        const now = event.timeStamp;
        const maxGap = burst?.active ? SCANNER_ACTIVE_KEY_GAP : SCANNER_MAX_KEY_GAP;
        if (!burst || burst.target !== target || now - burst.lastTime > maxGap) {
            this._clearBurst();
            this._burst = {
                target,
                startValue: target.value ?? "",
                chars: event.key,
                lastTime: now,
                fast: 0,
                active: false,
            };
            return; // primera tecla: se escribe con normalidad
        }

        burst.chars += event.key;
        burst.fast += 1;
        burst.lastTime = now;
        if (!burst.active && burst.fast >= 2) {
            burst.active = true;
            if ("value" in target) {
                target.value = burst.startValue;
                target.dispatchEvent(new Event("input", { bubbles: true }));
            }
        }
        if (burst.active) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            // Lectores sin Enter final: se da por terminado tras una pausa
            clearTimeout(this._burstTimer);
            this._burstTimer = setTimeout(() => this._finishBurst(), SCANNER_FLUSH_DELAY);
        }
    },

    _clearBurst() {
        clearTimeout(this._burstTimer);
        this._burstTimer = null;
        this._burst = null;
    },

    _finishBurst() {
        const burst = this._burst;
        this._clearBurst();
        if (!burst?.active) {
            return;
        }
        const barcode = cleanBarcode(burst.chars).trim();
        if (barcode.length >= MIN_BARCODE_LENGTH) {
            this._handledBarcode = { barcode, at: Date.now() };
            // Cierra el desplegable del autocompletado y saca el foco del campo
            burst.target.blur?.();
            this._processScannedBarcode(barcode);
        }
    },

    async onBarcodeScanned(event) {
        // Escaneo emitido por el servicio de códigos (p. ej. con el foco fuera de
        // los campos). Si ya lo ha tratado la detección por ráfaga, se ignora.
        const { barcode: rawBarcode, target } = event.detail;
        const barcode = cleanBarcode(rawBarcode || "").trim();
        if (barcode.length < MIN_BARCODE_LENGTH) {
            return;
        }
        if (target !== document.body && !this.formElement?.contains(target)) {
            return;
        }
        const handled = this._handledBarcode;
        if (handled && handled.barcode === barcode && Date.now() - handled.at < 2000) {
            return;
        }
        this._clearPendingBarcodeCapture();
        return this._processScannedBarcode(barcode);
    },

    async _processScannedBarcode(barcode) {
        if (this._scanBusy) {
            return;
        }
        this._scanBusy = true;
        try {
            // Con una línea en edición el onchange del escaneo dejaba una línea
            // vacía sin producto: se cierra la edición antes.
            const lines = this.props.record?.data?.lines;
            if (lines?.editedRecord) {
                try {
                    await lines.leaveEditMode({ canAbandon: false });
                } catch (error) {
                    console.warn("No se pudo cerrar la línea en edición antes de escanear", error);
                }
            }
            const previousLinesSignature = this._getOrderLinesSignature();
            await this.props.record.update({ [this.props.name]: barcode });
            if (previousLinesSignature !== this._getOrderLinesSignature()) {
                this._notifySuccessfulScan(barcode);
            }
        } finally {
            this._scanBusy = false;
        }
    },
});
