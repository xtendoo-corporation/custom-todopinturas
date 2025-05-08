import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { LocationLineDialog } from "./location_line_dialog";
import { LocationSelectionDialog } from "@todopintura_pos_custom/js/location_selection_dialog";
import { registry } from "@web/core/registry";

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

async crearPedidoyAlbaran() {
    const pos = this.env.services.pos;
    const order = pos.get_order();
    if (!order) {
        this.env.services.notification.add(_t("No hay pedido seleccionado."), { type: "danger" });
        return;
    }

    // Verificar conectividad antes de proceder
    if (this.env.services.pos.data.network.offline) {
        this.env.services.notification.add(_t("No se puede crear pedido a crédito en modo offline. Verifica tu conexión a internet."), { type: "danger" });
        return;
    }

    try {
        // Añadir flag para identificar como pedido a crédito
        order.to_credit = true;
        order.state = "to_credit";

        // Asegurarse de que todas las líneas tengan datos necesarios
        order.recomputeOrderData();

        // Forzar sincronización con el servidor
        await pos.syncAllOrders({ orders: [order], throw: true });

        // Eliminar de la interfaz tras confirmación exitosa
        pos.removePendingOrder(order);
        pos.removeOrder(order, false);

        this.env.services.notification.add(_t("Pedido confirmado como crédito y quitado de la sesión."), { type: "success" });
    } catch (error) {
        this.env.services.notification.add(_t("Error al procesar el pedido como crédito: ") + (error.message || error.data?.message || "Error desconocido"), { type: "danger" });
        console.error("Error al crear pedido a crédito:", error);
    }
}
 });
