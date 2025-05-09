/** @odoo-module */

import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { Component } from "@odoo/owl";
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
