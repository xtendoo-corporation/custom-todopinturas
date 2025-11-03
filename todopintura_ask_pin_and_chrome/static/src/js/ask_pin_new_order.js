/** @odoo-module **/
console.info('[todopintura] ask_pin_new_order.js asset executing');

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { _t } from "@web/core/l10n/translation";

console.log('[todopintura] 🔍 PosStore disponible:', !!PosStore);
console.log('[todopintura] 🔍 PosStore.prototype disponible:', !!PosStore.prototype);
console.log('[todopintura] 🔍 Métodos en PosStore.prototype:', Object.getOwnPropertyNames(PosStore.prototype).slice(0, 10));

// Patch del PosStore para interceptar la creación de órdenes
console.log('[todopintura] 📝 Aplicando patch a PosStore.prototype...');

patch(PosStore.prototype, {

    /**
     * Setup - Inicializar el contador de órdenes
     */
    setup() {
        super.setup(...arguments);

        // Flag para evitar solicitudes concurrentes
        this._isRequestingPin = false;

        // Inicializar el contador basándonos en las órdenes existentes
        // Al abrir el POS, puede que ya exista una orden creada automáticamente
        const existingOrders = this.models?.['pos.order']?.getAll?.() || [];
        this._orderCreationCount = existingOrders.length;

        console.log('[todopintura] ✅ PosStore setup - contador inicializado en:', this._orderCreationCount);
        console.log('[todopintura] Órdenes existentes al iniciar:', existingOrders.length);
    },

    /**
     * Método auxiliar para solicitar PIN antes de crear una orden
     */
    async _askPinBeforeOrder() {
        console.log('[todopintura] 🔐 _askPinBeforeOrder - Solicitando PIN');

        if (this._isRequestingPin) {
            console.log('[todopintura] Ya hay una solicitud de PIN en curso');
            return false;
        }

        this._isRequestingPin = true;
        try {
            // Obtener todos los empleados
            const allEmployees = this.models['hr.employee'].getAll();

            if (!allEmployees || allEmployees.length === 0) {
                console.error('[todopintura] ❌ No hay empleados disponibles');
                this.notification.add(_t('No hay empleados disponibles'), { type: 'danger' });
                return false;
            }

            console.log('[todopintura] Total empleados:', allEmployees.length);

            let employee = null;
            let attempts = 0;
            const maxAttempts = 100; // Permitir muchos intentos

            // Bucle hasta que se seleccione un empleado válido
            while (!employee && attempts < maxAttempts) {
                attempts++;
                console.log('[todopintura] Intento de selección de empleado:', attempts);

                // Mostrar popup de selección de cajero (NO se puede cerrar con ESC gracias al patch)
                employee = await makeAwaitable(this.dialog, CashierSelectionPopup, {
                    currentCashier: this.getCashier() || undefined,
                    employees: allEmployees,
                });

                if (!employee) {
                    console.log('[todopintura] ⚠️ No se seleccionó empleado, mostrando advertencia...');
                    this.notification.add(_t('Debes seleccionar un empleado para continuar'), {
                        type: 'warning',
                        sticky: true, // Mantener visible
                    });
                    // Esperar un momento antes de volver a mostrar el diálogo
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            }

            if (!employee) {
                console.error('[todopintura] ❌ No se pudo seleccionar empleado después de', maxAttempts, 'intentos');
                return false;
            }

            console.log('[todopintura] ✅ Empleado seleccionado:', employee.name);

            // Verificar PIN si el empleado lo tiene
            if (employee._pin) {
                console.log('[todopintura] 🔑 Solicitando PIN...');

                let pinValid = false;
                let pinAttempts = 0;
                const maxPinAttempts = 3;

                while (!pinValid && pinAttempts < maxPinAttempts) {
                    pinAttempts++;
                    console.log('[todopintura] Intento de PIN:', pinAttempts, 'de', maxPinAttempts);

                    const inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                        formatDisplayedValue: (x) => x.replace(/./g, "•"),
                        title: _t('PIN de %s', employee.name),
                    });

                    if (!inputPin) {
                        console.log('[todopintura] ⚠️ No se introdujo PIN');
                        this.notification.add(_t('Debes introducir el PIN para continuar'), {
                            type: 'warning',
                            sticky: true,
                        });
                        await new Promise(resolve => setTimeout(resolve, 500));
                        continue;
                    }

                    // Validar PIN (Odoo usa SHA1 hash)
                    /* global Sha1 */
                    if (employee._pin !== Sha1.hash(inputPin)) {
                        console.log('[todopintura] ❌ PIN incorrecto');
                        this.notification.add(_t('PIN incorrecto. Intento %s de %s', pinAttempts, maxPinAttempts), {
                            type: 'warning',
                        });
                        await new Promise(resolve => setTimeout(resolve, 500));
                        continue;
                    }

                    pinValid = true;
                    console.log('[todopintura] ✅ PIN correcto');
                }

                if (!pinValid) {
                    console.error('[todopintura] ❌ PIN incorrecto después de', maxPinAttempts, 'intentos');
                    this.notification.add(_t('Demasiados intentos fallidos'), { type: 'danger' });
                    return false;
                }
            }

            // El empleado fue seleccionado y el PIN validado, establecerlo
            console.log('[todopintura] 📝 Estableciendo cajero:', employee.name);
            this.setCashier(employee);
            return true;

        } catch (error) {
            console.error('[todopintura] ❌ Error en selección de empleado:', error);
            console.error('[todopintura] ❌ Stack:', error.stack);
            return false;
        } finally {
            this._isRequestingPin = false;
        }
    },

    /**
     * Override del método addNewOrder (camelCase) - Este es el que se llama en Odoo 19
     */
    async addNewOrder() {
        console.log('[todopintura] ⭐ addNewOrder interceptado - Contador ANTES:', this._orderCreationCount);

        // Evitar solicitudes concurrentes
        if (this._isRequestingPin) {
            console.log('[todopintura] Ya hay una solicitud de PIN en curso, saltando...');
            return await super.addNewOrder(...arguments);
        }

        // Determinar si debemos solicitar PIN (no en la primera orden de la sesión)
        const shouldAskPin = this._orderCreationCount > 0;
        console.log('[todopintura] ¿Solicitar PIN?:', shouldAskPin, '(creando órden #' + (this._orderCreationCount + 1) + ')');

        // Si debemos pedir PIN, hacerlo ANTES de crear la orden
        if (shouldAskPin && this.config.module_pos_hr) {
            console.log('[todopintura] 🔐 Solicitando selección de cajero con PIN ANTES de crear orden');

            const success = await this._askPinBeforeOrder();
            if (!success) {
                console.log('[todopintura] ❌ Validación de PIN fallida, cancelando creación de orden');
                return;
            }
        } else if (shouldAskPin && !this.config.module_pos_hr) {
            console.log('[todopintura] ⚠️ pos_hr no está habilitado, no se puede solicitar PIN');
        } else {
            console.log('[todopintura] Primera orden de la sesión, no se solicita PIN');
        }

        // Crear la orden
        console.log('[todopintura] Llamando a super.addNewOrder()');
        const result = await super.addNewOrder(...arguments);

        // IMPORTANTE: Incrementar el contador DESPUÉS de crear la orden exitosamente
        this._orderCreationCount++;
        console.log('[todopintura] ✅ Orden creada - Contador DESPUÉS:', this._orderCreationCount);

        return result;
    },

    /**
     * Override de getEmptyOrder - Método que se llama al completar una orden
     * Este es el que probablemente se llama cuando pulsas "Nuevo Pedido" después de una venta
     */
    async getEmptyOrder() {
        console.log('[todopintura] ⭐ getEmptyOrder interceptado - Contador:', this._orderCreationCount);

        // Si ya hay órdenes creadas, solicitar PIN antes de obtener una orden vacía
        if (this._orderCreationCount > 0 && this.config.module_pos_hr) {
            console.log('[todopintura] 🔐 Solicitando PIN antes de crear nueva orden (desde getEmptyOrder)');

            // Bucle hasta que se valide correctamente el PIN
            let success = false;
            while (!success) {
                success = await this._askPinBeforeOrder();
                if (!success) {
                    console.log('[todopintura] ⚠️ Validación de PIN fallida, intentando de nuevo...');
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }

            console.log('[todopintura] ✅ PIN validado correctamente');
            // Incrementar contador después de validar
            this._orderCreationCount++;
        }

        // Llamar al método original
        const result = await super.getEmptyOrder(...arguments);
        console.log('[todopintura] ✅ getEmptyOrder completado');

        return result;
    },
});

console.log('[todopintura] ✅ Patch aplicado correctamente');
console.log('[todopintura] 🔍 addNewOrder en prototype:', typeof PosStore.prototype.addNewOrder);
