import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { LocationLineDialog } from "./location_line_dialog";
import { LocationSelectionDialog } from "@todopintura_pos_custom/js/location_selection_dialog";
patch(ControlButtons.prototype, {
 async cambiarUbicacionLinea() {
        const order = this.pos.get_order();
        const selectedLine = order.get_selected_orderline();

        if (!selectedLine) {
            this.notification.add(_t("Selecciona una línea de pedido primero"), {
                type: "warning",
            });
            return;
        }

        try {
            // Obtener ubicaciones
            let locations = await this.env.services.orm.call(
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

            // Obtener inventario para este producto específico
            const product = selectedLine.get_product();
            const locationIds = locations.map(loc => loc.id);
            let inventoryData = {};

            try {
                const inventory = await this.env.services.orm.call(
                    'stock.quant',
                    'get_products_in_all_locations',
                    [[product.id], locationIds],
                );

                if (inventory && inventory.length > 0) {
                    for (const item of inventory) {
                        if (!inventoryData[item.location_id]) {
                            inventoryData[item.location_id] = [];
                        }
                        inventoryData[item.location_id].push(item);
                    }
                }
            } catch (error) {
                console.error("Error al obtener inventario:", error);
            }

            // Mostrar diálogo personalizado para seleccionar ubicación
             const selectedLocation = await new Promise(resolve => {
                this.env.services.dialog.add(LocationLineDialog, {
                    title: _t("Seleccionar Ubicación"),
                    locations: locations,
                    inventoryData: inventoryData,
                    confirm: (location) => {
                        resolve(location);
                    },
                    close: () => {
                        resolve(null);
                    }
                });
            });

           if (selectedLocation) {
                console.log("Ubicación seleccionada:", selectedLocation);
                console.log("Id de objeto ubicación:", selectedLocation.id);
                console.log("Nombre de objeto ubicación:", selectedLocation.name);
                console.log("Tipo de objeto ubicación:", typeof selectedLocation);
                // Usar el método set_location para actualizar la línea
                if (selectedLocation.id && selectedLocation.name) {
                    selectedLine.set_location(
                    selectedLocation.id ? Number(selectedLocation.id) : null,
                    selectedLocation.name ? String(selectedLocation.name) : ""
                );
                } else {
                    selectedLine.locationId = Number(selectedLocation.id);
                    selectedLine.locationName = String(selectedLocation.name);
                    order.trigger('change', order);
                }

                this.notification.add(_t("Ubicación actualizada correctamente"), {
                    type: "success",
                });
            }
        } catch (error) {
            this.notification.add(_t("Error al cambiar la ubicación: ") + (error.message || error), {
                type: "danger",
            });
            console.error("Error al cambiar ubicación:", error);
        }
    },
//    async clickNuevoBotonAlmacen() {
//        const order = this.pos.get_order();
//
//        if (!order || order.is_empty()) {
//            this.notification.add(_t("No hay productos en el pedido actual"), {
//                type: "warning",
//            });
//            return;
//        }
//
//        try {
//            const partner = order.get_partner();
//            if (!partner) {
//                this.notification.add(_t("Por favor, selecciona un cliente para el pedido"), {
//                    type: "warning",
//                });
//                return;
//            }
//
//            // Obtener las líneas con ubicación asignada
//            const orderLinesWithLocation = order.get_orderlines().filter(line => {
//                return line.locationData &&
//                       line.locationData.id !== null &&
//                       line.locationData.id !== undefined &&
//                       line.locationData.name !== "";
//            });
//
//            // Crear líneas de pedido (común para ambos casos)
//            const allOrderLines = [];
//            for (const line of order.get_orderlines()) {
//                const product = line.get_product();
//                const taxIds = [];
//                if (product.taxes_id && product.taxes_id.length) {
//                    for (const tax of product.taxes_id) {
//                        taxIds.push(typeof tax === 'object' ? tax.id : tax);
//                    }
//                }
//
//                allOrderLines.push([0, 0, {
//                    product_id: product.id,
//                    product_uom_qty: line.get_quantity(),
//                    price_unit: line.get_unit_price(),
//                    discount: line.get_discount(),
//                    tax_id: [[6, 0, taxIds]]
//                }]);
//            }
//
//            // Obtener warehouse_id
//            let warehouseId = false;
//            if (this.pos.config && this.pos.config.warehouse_id) {
//                warehouseId = Array.isArray(this.pos.config.warehouse_id)
//                    ? this.pos.config.warehouse_id[0]
//                    : this.pos.config.warehouse_id;
//            }
//
//            // Crear datos base para la venta
//            const saleData = {
//                partner_id: partner.id,
//                order_line: allOrderLines,
//                origin: `POS ${this.pos.config?.name || 'Desconocido'}`,
//                user_id: this.pos.user?.id || false,
//                auto_validate_picking: true
//            };
//
//            if (warehouseId) {
//                saleData.warehouse_id = warehouseId;
//            }
//
//            // Guardar referencia al pedido actual
//            const currentOrder = order;
//
//            // BIFURCACIÓN: Decidir qué método usar según si hay líneas con ubicación o no
//            if (orderLinesWithLocation.length === 0) {
//                // CASO 1: No hay líneas con ubicación - Crear venta estándar
//                const confirmed = await new Promise(resolve => {
//                    this.env.services.dialog.add(ConfirmationDialog, {
//                        title: _t("Crear venta estándar"),
//                        body: _t("No hay líneas con ubicación diferente. ¿Desea crear una venta estándar con un solo albarán?"),
//                        confirm: () => resolve(true),
//                        cancel: () => resolve(false)
//                    });
//                });
//
//                if (!confirmed) {
//                    this.notification.add(_t("Operación cancelada"), {
//                        type: "info"
//                    });
//                    return;
//                }
//
//                // Llamar al método para venta estándar
//                await this.env.services.orm.call(
//                    'sale.order',
//                    'create_sale_from_pos',
//                    [saleData]
//                );
//            } else {
//                // CASO 2: Hay líneas con ubicación - Crear venta con múltiples albaranes
//                // Obtener ubicaciones disponibles
//                let locations = [];
//                try {
//                    locations = await this.env.services.orm.call(
//                        'stock.location',
//                        'search_read',
//                        [[['usage', '=', 'internal'], ['active', '=', true]]],
//                        {fields: ['id', 'name', 'complete_name', 'warehouse_id']}
//                    );
//
//                    if (!locations || locations.length === 0) {
//                        this.notification.add(_t("No se encontraron ubicaciones disponibles"), {
//                            type: "warning",
//                        });
//                        return;
//                    }
//                } catch (rpcError) {
//                    console.error("Error al obtener ubicaciones:", rpcError);
//                    this.notification.add(_t("Error al obtener las ubicaciones"), {
//                        type: "danger",
//                    });
//                    return;
//                }
//
//                // Crear objeto de preasignaciones
//                const preassignedLocations = {};
//                orderLinesWithLocation.forEach(line => {
//                    preassignedLocations[line.get_product().id] = line.locationData?.id || null;
//                });
//
//                // Mostrar diálogo para confirmar ubicaciones
//                const dialogResult = await new Promise(resolve => {
//                    this.env.services.dialog.add(LocationSelectionDialog, {
//                        title: _t("Asignar productos a ubicaciones"),
//                        bodyMessage: _t("Confirme o modifique las ubicaciones de los productos:"),
//                        locations: locations,
//                        orderProducts: orderLinesWithLocation.map(line => ({
//                            id: line.get_product().id,
//                            name: line.get_product().display_name,
//                            quantity: line.get_quantity()
//                        })),
//                        preassignedLocations: preassignedLocations,
//                        onConfirm: (result) => {
//                            resolve({confirmed: true, data: result});
//                        },
//                        onCancel: () => {
//                            resolve({confirmed: false});
//                        },
//                    });
//                });
//
//                if (!dialogResult.confirmed) {
//                    this.notification.add(_t("Operación cancelada"), {
//                        type: "info",
//                    });
//                    return;
//                }
//
//                // Añadir las ubicaciones a los datos de venta
//                saleData.products_by_location = dialogResult.data;
//
//                // Llamar al método para venta con múltiples albaranes
//                await this.env.services.orm.call(
//                    'sale.order',
//                    'create_sale_with_multiple_pickings_from_pos',
//                    [saleData]
//                );
//            }
//
//            // Limpiar el pedido actual
//            this.pos.add_new_order();
//            if (this.pos.removeOrder) {
//                this.pos.removeOrder(currentOrder);
//            } else if (this.pos.delete_current_order) {
//                this.pos.delete_current_order();
//            }
//
//            if (this.pos.db && this.pos.db.remove_order) {
//                this.pos.db.remove_order(currentOrder.uid);
//            }
//
//            // Mensaje de éxito
//            const successMessage = orderLinesWithLocation.length > 0
//                ? _t("Venta creada con albaranes separados por ubicación")
//                : _t("Venta estándar creada correctamente");
//
//            this.notification.add(successMessage, {
//                type: "success",
//            });
//        } catch (error) {
//            this.notification.add(_t("Error en la operación: ") + (error.message || error), {
//                type: "danger",
//            });
//            console.error("Error general:", error);
//        }
//    },

 });
