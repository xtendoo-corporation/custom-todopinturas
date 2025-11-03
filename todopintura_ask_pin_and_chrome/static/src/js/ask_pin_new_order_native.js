/** @odoo-module **/
console.info('[todopintura] ask_pin_new_order_native.js asset executing');

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { askQuestion } from "@point_of_sale/app/utils/ask_question";

// Contador de órdenes creadas
let orderCount = 0;
let isRequestingPin = false;

patch(PosStore.prototype, {

    async addNewOrder() {
        console.log('[todopintura] ⭐ addNewOrder interceptado - Orden #' + (orderCount + 1));

        if (isRequestingPin) {
            console.log('[todopintura] Ya hay una solicitud de PIN en curso');
            return await super.addNewOrder(...arguments);
        }

        const hasExistingOrders = orderCount > 0;
        console.log('[todopintura] Órdenes creadas anteriormente:', orderCount);

        if (hasExistingOrders) {
            console.log('[todopintura] 🔐 Solicitando cambio de cajero');

            isRequestingPin = true;
            try {
                // Obtener empleados
                const employees = this.models && this.models['hr.employee'] ?
                                 this.models['hr.employee'].getAll() : [];

                if (!employees || employees.length === 0) {
                    console.error('[todopintura] ❌ No hay empleados disponibles');
                    isRequestingPin = false;
                    return;
                }

                console.log('[todopintura] Empleados disponibles:', employees.length);

                // Usar askQuestion para mostrar un diálogo de selección
                const employeesList = employees.map(emp => ({
                    id: emp.id,
                    name: emp.name,
                    item: emp,
                }));

                // Mostrar selección de empleados usando askQuestion
                const answer = await askQuestion(this, {
                    title: 'Seleccionar Cajero para Nueva Venta',
                    body: 'Selecciona el empleado que realizará la venta',
                    list: employeesList.map(emp => ({
                        label: emp.name,
                        item: emp.item,
                    })),
                });

                console.log('[todopintura] Respuesta de askQuestion:', answer);

                if (!answer || !answer.item) {
                    console.log('[todopintura] ❌ No se seleccionó empleado');
                    isRequestingPin = false;
                    return;
                }

                const selectedEmployee = answer.item;
                console.log('[todopintura] ✅ Empleado seleccionado:', selectedEmployee.name);

                // Verificar PIN si el empleado lo tiene
                if (selectedEmployee.pin && selectedEmployee.pin !== '' && selectedEmployee.pin !== '0') {
                    console.log('[todopintura] 🔑 Solicitando PIN...');

                    const pinAnswer = await askQuestion(this, {
                        title: `PIN de ${selectedEmployee.name}`,
                        body: 'Introduce el PIN del empleado',
                        isPassword: true,
                    });

                    console.log('[todopintura] PIN introducido');

                    if (!pinAnswer || !pinAnswer.payload) {
                        console.log('[todopintura] ❌ No se introdujo PIN');
                        isRequestingPin = false;
                        return;
                    }

                    const enteredPin = String(pinAnswer.payload).trim();
                    const expectedPin = String(selectedEmployee.pin).trim();

                    if (enteredPin !== expectedPin) {
                        console.log('[todopintura] ❌ PIN incorrecto');
                        alert('PIN incorrecto');
                        isRequestingPin = false;
                        return;
                    }

                    console.log('[todopintura] ✅ PIN correcto');
                }

                // Establecer el empleado como cajero
                console.log('[todopintura] 📝 Estableciendo cajero:', selectedEmployee.name);
                if (this.set_cashier) {
                    this.set_cashier(selectedEmployee);
                } else {
                    this.cashier = selectedEmployee;
                }

            } catch (error) {
                console.error('[todopintura] ❌ Error:', error);
                console.error('[todopintura] ❌ Stack:', error.stack);
            } finally {
                isRequestingPin = false;
            }
        }

        const result = await super.addNewOrder(...arguments);
        orderCount++;
        console.log('[todopintura] ✅ Orden creada. Total:', orderCount);

        return result;
    },
});

