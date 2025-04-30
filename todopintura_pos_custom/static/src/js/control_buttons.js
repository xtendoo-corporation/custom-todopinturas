import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { LocationSelectionDialog } from "./location_selection_dialog";

patch(ControlButtons.prototype, {
    async clickNuevoBoton() {
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

            // Usar la ubicación de stock del almacén asociado al punto de venta
            let selectedLocation = this.pos.config.warehouse_id && this.pos.config.stock_location_id ?
                {id: this.pos.config.stock_location_id[0]} : {id: false};

            // Guardar una referencia al pedido actual
            const currentOrder = order;

            // Preparar líneas en formato correcto para venta estándar
            const orderLines = [];
            for (const line of order.get_orderlines()) {
                const product = line.get_product();
                if (!product) continue;

                const taxIds = [];
                if (product.taxes_id && product.taxes_id.length) {
                    for (const tax of product.taxes_id) {
                        taxIds.push(typeof tax === 'object' ? tax.id : tax);
                    }
                }

                orderLines.push([0, 0, {
                    product_id: product.id,
                    product_uom_qty: line.get_quantity(),
                    price_unit: line.get_unit_price(),
                    discount: line.get_discount(),
                    tax_id: [[6, 0, taxIds]]
                }]);
            }

            // Obtener warehouse_id de forma segura
            let warehouseId = false;
            if (this.pos.config && this.pos.config.warehouse_id) {
                warehouseId = Array.isArray(this.pos.config.warehouse_id)
                    ? this.pos.config.warehouse_id[0]
                    : this.pos.config.warehouse_id;
            }

            // Datos para venta estándar
         const saleData = {
            partner_id: partner.id,
            order_line: orderLines,
            origin: `POS ${this.pos.config?.name || 'Desconocido'}`,
            user_id: this.pos.user?.id || false,
            auto_validate_picking: true,
            custom_location_id: selectedLocation.id
        };


        if (warehouseId) {
            saleData.warehouse_id = warehouseId;
        }

        if (warehouseId) {
            saleData.warehouse_id = warehouseId;
        }

        // Crear la venta estándar y validar albarán
        const resultado = await this.env.services.orm.call(
            'sale.order',
            'create_sale_from_pos',
            [saleData]  // Pasar la ubicación como parámetro separado
        );

            // Crear un nuevo pedido vacío primero
            this.pos.add_new_order();

            // Ahora eliminar el pedido anterior de forma segura
            if (this.pos.removeOrder) {
                this.pos.removeOrder(currentOrder);
            } else if (this.pos.delete_current_order) {
                // Compatibilidad con versiones anteriores
                this.pos.delete_current_order();
            }

            // Eliminar también de la lista de órdenes
            if (this.pos.db && this.pos.db.remove_order) {
                this.pos.db.remove_order(currentOrder.uid);
            }

            this.notification.add(_t("Venta y albarán validados correctamente"), {
                type: "success",
            });

        } catch (error) {
            this.notification.add(_t("Error al crear la venta: ") + (error.message || error), {
                type: "danger",
            });
            console.error("Error al crear la venta y albarán:", error);

            if (error.data && error.data.debug) {
                console.error("Error detallado:", error.data.debug);
            }
        }
    },

   async clickNuevoBotonAlmacen() {
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

        // Obtener la lista de productos en el pedido
        const orderProducts = order.get_orderlines().map(line => {
            return {
                id: line.get_product().id,
                name: line.get_product().display_name,
                quantity: line.get_quantity()
            };
        });

        // Obtener ubicaciones
        let locations = [];
        try {
            locations = await this.env.services.orm.call(
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

        // Obtener inventario
        let inventoryData = {};
        const productIds = orderProducts.map(p => p.id);
        const locationIds = locations.map(loc => loc.id);

        // Intentar obtener inventario
        try {
            const allInventory = await this.env.services.orm.call(
                'stock.quant',
                'get_products_in_all_locations',
                [productIds, locationIds],
            );
            console.log("Respuesta del servidor:", allInventory);

            if (allInventory && allInventory.length > 0) {
                for (const item of allInventory) {
                    if (!inventoryData[item.location_id]) {
                        inventoryData[item.location_id] = [];
                    }
                    inventoryData[item.location_id].push(item);
                }
            }
        } catch (error) {
            console.error("Error detallado:", error);
            if (error.data && error.data.debug) {
                console.error("Stack trace del servidor:", error.data.debug);
            }
        }

        // Usar promesa para manejar el diálogo
        const productsByLocation = await new Promise(resolve => {
            let dialogClosed = false;

            this.env.services.dialog.add(LocationSelectionDialog, {
                title: _t("Asignar productos a ubicaciones"),
                bodyMessage: _t("Selecciona la ubicación de origen para cada producto:"),
                locations: locations,
                orderProducts: orderProducts,
                inventoryData: inventoryData,
                onConfirm: (productsByLocation) => {
                    dialogClosed = true;
                    resolve(productsByLocation);
                },
                onCancel: () => {
                    dialogClosed = true;
                    resolve(null);
                },
            });
        });

        if (productsByLocation) {
            // Guardar referencia al pedido actual
            const currentOrder = order;

            // Ahora procesamos las ventas separadas por ubicación
               try {
                // Crear todas las líneas de pedido
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

                // Crear datos para esta venta
                const saleData = {
                    partner_id: partner.id,
                    order_line: allOrderLines,
                    origin: `POS ${this.pos.config?.name || 'Desconocido'}`,
                    user_id: this.pos.user?.id || false,
                    auto_validate_picking: true,
                    products_by_location: productsByLocation
                };

                if (warehouseId) {
                    saleData.warehouse_id = warehouseId;
                }

                // Llamar al nuevo método
                await this.env.services.orm.call(
                    'sale.order',
                    'create_sale_with_multiple_pickings_from_pos',
                    [saleData]
                );

                // Limpiar el pedido actual
                this.pos.add_new_order();
                if (this.pos.removeOrder) {
                    this.pos.removeOrder(currentOrder);
                } else if (this.pos.delete_current_order) {
                    this.pos.delete_current_order();
                }

                if (this.pos.db && this.pos.db.remove_order) {
                    this.pos.db.remove_order(currentOrder.uid);
                }

                this.notification.add(_t("Venta creada con albaranes separados por ubicación"), {
                    type: "success",
                });
            } catch (error) {
                this.notification.add(_t("Error al crear la venta: ") + (error.message || error), {
                    type: "danger",
                });
                console.error("Error al crear la venta y albarán:", error);

                if (error.data && error.data.debug) {
                    console.error("Error detallado:", error.data.debug);
                }
            }
        } else {
            this.notification.add(_t("Operación cancelada"), {
                type: "info",
            });
        }
    } catch (error) {
        this.notification.add(_t("Error en la operación: ") + (error.message || error), {
            type: "danger",
        });
        console.error("Error general:", error);
    }
}
 });
