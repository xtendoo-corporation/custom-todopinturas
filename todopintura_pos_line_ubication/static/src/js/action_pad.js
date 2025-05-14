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

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    },

    async clickNewButtonStore() {
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
                'check_credit_limit',  // Ahora usa el método público sin guion bajo
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

            // Crear datos base para la venta
            const saleData = {
                partner_id: partner.id,
                order_line: allOrderLines,
                origin: `POS ${this.pos.config?.name || 'Desconocido'}`,
                user_id: this.pos.user?.id || false,
                auto_validate_picking: true
            };

            if (warehouseId) {
                saleData.warehouse_id = warehouseId;
            }

            // Guardar referencia al pedido actual
            const currentOrder = order;

            // BIFURCACIÓN: Decidir qué método usar según si hay líneas con ubicación o no
            if (orderLinesWithLocation.length === 0) {
                // Llamar al método para venta estándar
                await this.orm.call(
                    'sale.order',
                    'create_sale_from_pos',
                    [saleData]
                );
             }
             else {
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
                await this.orm.call(
                    'sale.order',
                    'create_sale_with_multiple_pickings_from_pos',
                    [saleData]
                );
            }

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
        } catch (error) {
            this.notification.add(_t("Error en la operación: ") + (error.message || error), {
                type: "danger",
            });
            console.error("Error general:", error);
        }
    }
});
