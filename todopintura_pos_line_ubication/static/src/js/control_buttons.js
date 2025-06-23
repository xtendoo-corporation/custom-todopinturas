import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { LocationLineDialog } from "./location_line_dialog";
import { LocationSelectionDialog } from "@todopintura_pos_custom/js/location_selection_dialog";
patch(ControlButtons.prototype, {
 async changeUbicationLine() {
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
//    async creditSale() {
//    const order = this.pos.get_order();
//
//    // Verificar si hay una orden y si tiene líneas
//    if (!order || !order.get_orderlines().length) {
//        this.notification.add(_t("No hay productos en el carrito"), {
//            type: "warning",
//        });
//        return;
//    }
//
//    // Verificar si hay un cliente seleccionado
//    if (!order.get_partner()) {
//        this.notification.add(_t("Debe seleccionar un cliente para la venta a crédito"), {
//            type: "warning",
//        });
//        return;
//    }
//
//    // Mostrar diálogo de confirmación
//    const confirmed = await new Promise(resolve => {
//        this.env.services.dialog.add(ConfirmationDialog, {
//            title: _t("Confirmación de venta a crédito"),
//            body: _t("¿Está seguro que desea crear una venta a crédito? Se generará un albarán sin confirmar."),
//            confirm: () => resolve(true),
//            cancel: () => resolve(false),
//        });
//    });
//
//    if (confirmed) {
//        try {
//            // Obtener los datos necesarios de la orden
//            const orderLines = order.get_orderlines().map(line => {
//                let taxIds = [];
//                try {
//                    // Intentamos diferentes formas de obtener los impuestos
//                    if (line.getTaxIds && typeof line.getTaxIds === 'function') {
//                        taxIds = line.getTaxIds();
//                    } else if (line.tax_ids) {
//                        taxIds = line.tax_ids;
//                    } else if (line.get_product().taxes_id) {
//                        taxIds = line.get_product().taxes_id;
//                    }
//                } catch (e) {
//                    console.error("Error al obtener impuestos:", e);
//                }
//
//                return {
//                    product_id: line.get_product().id,
//                    name: line.get_product().display_name,
//                    product_uom_qty: line.get_quantity(),
//                    price_unit: line.get_unit_price(),
//                    discount: line.get_discount(),
//                    tax_ids: taxIds
//                };
//            });
//
//            // Obtener el cajero actual del TPV
//            const currentCashier = this.pos.get_cashier();
//            let cashierId = false;
//
//            // Enviamos el ID del empleado directamente
//            if (currentCashier && currentCashier.id) {
//                cashierId = currentCashier.id;  // ID del empleado (no del usuario)
//                console.log("ID del empleado cajero:", cashierId);
//            } else {
//                console.warn("No se pudo obtener el ID del cajero:", currentCashier);
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
//            const orderData = {
//                partner_id: order.get_partner().id,
//                lines: orderLines,
//                origin: 'POS ' + order.name,
//                pos_reference: order.name,
//                employee_cashier_id: cashierId,
//                auto_validate_picking: false  // Explícitamente indicamos que no valide el albarán
//            };
//
//            if (warehouseId) {
//                orderData.warehouse_id = warehouseId;
//            }
//
//            // Llamar al método del servidor para crear la venta a crédito
//            const result = await this.env.services.orm.call(
//                'sale.order',
//                'create_credit_sale',
//                [orderData]
//            );
//
//            if (result && result.sale_id) {
//                // Limpiar la orden actual
//                this.pos.delete_current_order();
//
//                this.notification.add(_t("Venta a crédito creada correctamente. Referencia: ") + result.name, {
//                    type: "success",
//                });
//            } else {
//                this.notification.add(_t("Error al crear la venta a crédito"), {
//                    type: "danger",
//                });
//            }
//        } catch (error) {
//            this.notification.add(_t("Error al procesar la venta a crédito: ") + (error.message || error), {
//                type: "danger",
//            });
//            console.error("Error al procesar venta a crédito:", error);
//        }
//    }
//}

 });
