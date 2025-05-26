/** @odoo-module */

import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { Component, markup } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { LocationLineDialog } from "./location_line_dialog";
import { LocationSelectionDialog } from "@todopintura_pos_custom/js/location_selection_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { useState, useEffect } from "@odoo/owl";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ canCreateAlbaran: false, loading: false });
        // Solo se ejecuta cuando cambia el prop partner
        useEffect(() => {
            this._checkAlbaranButtonState();
        }, () => [this.props.partner]);
    },

    async _checkAlbaranButtonState() {
        this.state.loading = true;
        const order = this.pos.get_order();
        const partner = order && order.get_partner();
        if (!partner || !partner.credit_sale) {
            this.state.canCreateAlbaran = false;
            this.state.loading = false;
            return;
        }
        try {
            const result = await this.orm.call(
                "res.partner",
                "check_credit_location_matches_pos",
                [partner.id, this.pos.config.id]
            );
            this.state.canCreateAlbaran = !!(result && result.matches);
        } catch (e) {
            this.state.canCreateAlbaran = false;
        }
        this.state.loading = false;
    },

    async clickNewButtonStore() {
        if (!this.state.canCreateAlbaran) {
            this.notification.add(_t("No puedes crear albarán para este cliente o caja."), { type: "warning" });
            return;
        }
        const order = this.pos.get_order();

        if (!order || order.is_empty()) {
            this.notification.add(_t("No hay productos en el pedido actual"), {
                type: "warning",
            });
            return;
        }

        try {
            const partner = order.get_partner();
            if (!partner) {
                this.notification.add(_t("Por favor, selecciona un cliente para el pedido"), {
                    type: "warning",
                });
                return;
            }
            const creditCheckResult = await this.orm.call(
                'sale.order',
                'check_credit_limit',
                [partner.id, order.get_total_with_tax()]
            );

            if (creditCheckResult && creditCheckResult.credit_limit_exceeded) {
                // Mostrar diálogo de confirmación si se excede el límite
                const { confirmed } = await new Promise(resolve => {
                   this.dialog.add(ConfirmationDialog, {
                        title: _t("Advertencia de Límite de Crédito"),
                       body: markup(`
                            <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px; padding: 16px; margin-bottom: 10px;">
                                 <div style="display: flex; gap: 10px; align-items: flex-start; margin-bottom: 12px;">
                                    <i class="fa fa-exclamation-triangle" style="font-size: 24px; color: #856404;"></i>
                                    <span style="color: #856404; font-size: 16px; font-weight: bold;">${_t("El cliente ")}${creditCheckResult.partner_name}${_t("ha superado su límite de crédito.")}</span>
                                </div>
                                <div style="margin-left: 34px;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                        <span>${_t("Límite de crédito")}:</span>
                                        <span style="font-weight: bold;">${creditCheckResult.credit_limit.toFixed(2)} €</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                        <span>${_t("Crédito ya utilizado")}:</span>
                                        <span style="font-weight: bold;">${creditCheckResult.credit_used.toFixed(2)} €</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                        <span>${_t("Importe del pedido actual")}:</span>
                                        <span style="font-weight: bold;">${creditCheckResult.order_amount.toFixed(2)} €</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; background-color: #ffecb5; padding: 6px; border-radius: 4px; margin-top: 8px;">
                                        <span style="font-weight: bold;">${_t("Total crédito después de confirmar")}:</span>
                                        <span style="font-weight: bold; color: #cc0000;">${creditCheckResult.total_credit.toFixed(2)} €</span>
                                    </div>
                                </div>
                            </div>
                            <p style="text-align: center; font-weight: bold; margin-top: 15px;">${_t("¿Desea continuar con el pedido de todas formas?")}</p>
                        `),
                        confirm: () => resolve({ confirmed: true }),
                        cancel: () => resolve({ confirmed: false }),
                    });
                });

                if (!confirmed) {
                    return; // Cancelar la operación si el usuario no confirma
                }
            }

            // Obtener las líneas con ubicación asignada
            const orderLinesWithLocation = order.get_orderlines().filter(line => {
                return line.locationData &&
                       line.locationData.id !== null &&
                       line.locationData.id !== undefined &&
                       line.locationData.name !== "";
            });

            // Crear líneas de pedido (común para ambos casos)
            const allOrderLines = [];
            for (const line of order.get_orderlines()) {
                const product = line.get_product();
                const taxIds = [];
                if (product.taxes_id && product.taxes_id.length) {
                    for (const tax of product.taxes_id) {
                        taxIds.push(typeof tax === 'object' ? tax.id : tax);
                    }
                }

                allOrderLines.push([0, 0, {
                    product_id: product.id,
                    product_uom_qty: line.get_quantity(),
                    price_unit: line.get_unit_price(),
                    discount: line.get_discount(),
                    tax_id: [[6, 0, taxIds]]
                }]);
            }

            // Obtener warehouse_id
            let warehouseId = false;
            if (this.pos.config && this.pos.config.warehouse_id) {
                warehouseId = Array.isArray(this.pos.config.warehouse_id)
                    ? this.pos.config.warehouse_id[0]
                    : this.pos.config.warehouse_id;
            }

            // Obtener el cajero actual del TPV
           const currentCashier = this.pos.get_cashier();
            let cashierId = false;

            // Enviamos el ID del empleado directamente
            if (currentCashier && currentCashier.id) {
                cashierId = currentCashier.id;  // ID del empleado (no del usuario)
                console.log("ID del empleado cajero:", cashierId);
            } else {
                console.warn("No se pudo obtener el ID del cajero:", currentCashier);
            }

            // Crear datos base para la venta
            const saleData = {
                partner_id: partner.id,
                order_line: allOrderLines,
                origin: `POS ${this.pos.config?.name || 'Desconocido'}`,
                auto_validate_picking: true,
                // Enviar ID del empleado
                employee_cashier_id: cashierId  // Renombramos para distinguirlo del user_id
            };
            // Añadir la nota general del pedido POS a los datos de la venta
            if (order.general_note) {
                saleData.general_note = order.general_note;
                console.log("Añadiendo nota general a la venta:", order.general_note);
            }
            if (warehouseId) {
                saleData.warehouse_id = warehouseId;
            }

            // Guardar referencia al pedido actual
            const currentOrder = order;

            let result;
            // BIFURCACIÓN: Decidir qué método usar según si hay líneas con ubicación o no
            if (orderLinesWithLocation.length === 0) {
                // Llamar al método para venta estándar
                result = await this.orm.call(
                    'sale.order',
                    'create_sale_from_pos',
                    [saleData]
                );
             } else {
                // CASO 2: Hay líneas con ubicación - Crear venta con múltiples albaranes
                // Obtener ubicaciones disponibles
                let locations = [];
                try {
                    locations = await this.orm.call(
                        'stock.location',
                        'search_read',
                        [[['usage', '=', 'internal'], ['active', '=', true]]],
                        {fields: ['id', 'name', 'complete_name', 'warehouse_id']}
                    );

                    if (!locations || locations.length === 0) {
                        this.notification.add(_t("No se encontraron ubicaciones disponibles"), {
                            type: "warning",
                        });
                        return;
                    }
                } catch (rpcError) {
                    console.error("Error al obtener ubicaciones:", rpcError);
                    this.notification.add(_t("Error al obtener las ubicaciones"), {
                        type: "danger",
                    });
                    return;
                }

                // Crear objeto con formato invertido (locationId: [productIds])
                const preassignedLocations = {};
                orderLinesWithLocation.forEach(line => {
                    const productId = line.get_product().id;
                    const locationId = line.locationData?.id || null;

                    if (locationId !== null) {
                        // Crear array si no existe para esta ubicación
                        if (!preassignedLocations[locationId]) {
                            preassignedLocations[locationId] = [];
                        }
                        // Añadir el producto a esta ubicación
                        preassignedLocations[locationId].push(productId);
                    }
                });

                // Asignar directamente a los datos de venta sin mostrar diálogo
                saleData.products_by_location = preassignedLocations;

                // Llamar al método para venta con múltiples albaranes
                result = await this.orm.call(
                    'sale.order',
                    'create_sale_with_multiple_pickings_from_pos',
                    [saleData]
                );
            }

            // Si result contiene información sobre la venta y los albaranes
            const saleOrderId = result?.id;
            const pickingIds = result?.picking_ids || [];

            // Limpiar el pedido actual
            this.pos.add_new_order();
            if (this.pos.removeOrder) {
                this.pos.removeOrder(currentOrder);
            } else if (this.pos.delete_current_order) {
                this.pos.delete_current_order();
            }

            // Mensaje de éxito
            const successMessage = orderLinesWithLocation.length > 0
                ? _t("Venta creada con albaranes separados por ubicación")
                : _t("Venta estándar creada correctamente");

            this.notification.add(successMessage, {
                type: "success",
            });

            // Mostrar diálogo para imprimir albaranes si hay albaranes disponibles
if (pickingIds && pickingIds.length > 0) {
    const { action } = await new Promise(resolve => {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Albaranes generados"),
            body: markup(`
                <div class="py-2 text-center">
                    <p class="mb-3">${_t("La venta se ha creado correctamente.")}</p>
                    <p>${pickingIds.length > 1
                        ? _t("Se han generado ") + pickingIds.length + _t(" albaranes.")
                        : _t("Se ha generado un albarán.")}</p>
                    <p class="mt-3">${_t("¿Qué deseas hacer con los albaranes?")}</p>
                </div>
            `),
            confirmLabel: _t("Ver albaranes"),
            cancelLabel: _t("Cerrar"),
            confirm: () => resolve({ action: 'view' }),
            cancel: () => resolve({ action: 'close' }),
        });
    });

    if (action === 'view') {
        try {
            // Mostrar diálogo para elegir entre ver o imprimir
            const { selectedAction } = await new Promise(resolve => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Opciones de albaranes"),
                    body: _t("¿Deseas ver o imprimir los albaranes?"),
                    confirmLabel: _t("Ver"),
                    cancelLabel: _t("Imprimir"),
                    confirm: () => resolve({ selectedAction: 'view' }),
                    cancel: () => resolve({ selectedAction: 'print' })
                });
            });

            if (selectedAction === 'view') {
                // Código para ver albaranes
                let viewAction;
                if (pickingIds.length === 1) {
                    viewAction = {
                        type: 'ir.actions.act_window',
                        res_model: 'stock.picking',
                        res_id: pickingIds[0],
                        views: [[false, 'form']],
                        target: 'current',
                    };
                } else {
                    viewAction = {
                        type: 'ir.actions.act_window',
                        res_model: 'stock.picking',
                        domain: [['id', 'in', pickingIds]],
                        views: [[false, 'list'], [false, 'form']],
                        target: 'current',
                    };
                }
                await this.action.doAction(viewAction);
            } else {
                // Código corregido para imprimir albaranes
                // Código para imprimir albaranes - versión corregida
const printAction = {
    type: 'ir.actions.act_url',
    url: '/report/pdf/todopintura_pos_custom.report_sale_credit_slip/' + pickingIds.join(','),
    target: 'new'
};
await this.action.doAction(printAction);
            }
        } catch (error) {
            console.error("Error con los albaranes:", error);
            this.notification.add(_t("Ha ocurrido un error"), {
                type: "warning",
            });
        }
    }
} // Cierre del if pickingIds
        } catch (error) { // Este catch cierra el try principal del método
            console.error("Error al crear la venta:", error);
            this.notification.add(_t("Error al crear la venta"), {
                type: "danger",
            });
        }
    } // Cierre del método clickNewButtonStore
});
