import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class LocationSelectionDialog extends Dialog {
    static template = 'todopintura_pos_custom.LocationSelectionDialog';
    static components = { Dialog };
    static props = {
        ...Dialog.props,
        locations: { type: Array, optional: true },
        inventoryData: { type: Object, optional: true },
        orderProducts: { type: Array, optional: true },
        bodyMessage: { type: String, optional: true },
        slots: { type: Array, optional: true },
        onConfirm: { type: Function },
        onCancel: { type: Function, optional: true },
        close: { type: Function },
    };

    setup() {
        super.setup();
        console.log("setup LocationSelectionDialog");
        this.state = useState({
            productsByLocation: {},
            selectedLocations: []
        });

        // Inicializar todos los productos sin ubicación asignada
        if (this.props.orderProducts) {
            this.props.orderProducts.forEach(product => {
                this.state.productsByLocation[product.id] = null;
            });
        }
    }

    close() {
        // Limpiar el estado primero
        this.state.productsByLocation = {};
        this.state.selectedLocations = [];

        // Para diálogos en Odoo, generalmente usamos la función props.close
        if (typeof this.props.close === 'function') {
            this.props.close();
            return;
        }

        // Si no hay props.close, intentar con el método estándar
        try {
            super.close();
        } catch (error) {
            console.warn("Error al cerrar el diálogo:", error);
        }
    }

    // Método específico para manejar el cambio de ubicación
    handleProductLocationChange(productId, event) {
        const locationId = event.target.value ? parseInt(event.target.value) : null;
        this.toggleProductLocation(productId, locationId);
    }

    toggleProductLocation(productId, locationId) {
        this.state.productsByLocation[productId] = locationId;
        this._updateSelectedLocations();
    }

    _updateSelectedLocations() {
        const locations = new Set(
            Object.values(this.state.productsByLocation).filter(id => id !== null)
        );
        this.state.selectedLocations = Array.from(locations);
    }

    getSelectedProductsByLocation() {
        const result = {};

        for (const [productId, locationId] of Object.entries(this.state.productsByLocation)) {
            if (locationId !== null) {
                if (!result[locationId]) {
                    result[locationId] = [];
                }
                result[locationId].push(parseInt(productId));
            }
        }

        return result;
    }

    onClickConfirm() {
        const productsByLocation = this.getSelectedProductsByLocation();

        // Verificar productos sin asignar
        const unassignedCount = Object.values(this.state.productsByLocation)
            .filter(locationId => locationId === null).length;

        if (unassignedCount > 0 && this.props.orderProducts) {
            this.env.services.dialog.add(ConfirmationDialog, {
                title: _t("Productos sin asignar"),
                body: _t("Hay productos sin asignar a ubicaciones. ¿Desea continuar?"),
                confirm: () => {
                    this.props.onConfirm(productsByLocation);
                    this.close();
                },
                cancel: () => {}
            });
        } else {
            this.props.onConfirm(productsByLocation);
            this.close();
        }
    }

    onClickCancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
        this.close();
    }
}

registry.category("dialogs").add("locationSelectionDialog", LocationSelectionDialog);
