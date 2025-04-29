import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

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
                auto_validate_picking: true
            };

            if (warehouseId) {
                saleData.warehouse_id = warehouseId;
            }

            // Crear la venta estándar y validar albarán
            const resultado = await this.env.services.orm.call(
                'sale.order',
                'create_sale_from_pos',
                [saleData]
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

        // Mostrar un diálogo de confirmación inicial
        this.env.services.dialog.add(ConfirmationDialog, {
            title: _t("Seleccionar ubicación"),
            body: _t("¿Deseas continuar con la selección de la ubicación de origen para este pedido?"),
            confirmLabel: _t("Continuar"),
            cancelLabel: _t("Cancelar"),
            confirm: async () => {
                try {
                    // Obtener todas las ubicaciones activas
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

                    // Mostrar navegador de ubicaciones
                    const showLocationDialog = async (index) => {
                        if (index >= locations.length) {
                            this.notification.add(_t("No se ha seleccionado ninguna ubicación"), {
                                type: "info",
                            });
                            return;
                        }

                        const location = locations[index];
                        const totalLocations = locations.length;

                        // Obtener cantidades disponibles para los productos en esta ubicación
                        let productQuantities = [];
                        try {
                            const productIds = orderProducts.map(p => p.id);
                            productQuantities = await this.env.services.orm.call(
                                'stock.quant',
                                'get_product_quantities_in_location',
                                [productIds, location.id]
                            );
                        } catch (error) {
                            console.error("Error al obtener cantidades:", error);
                            productQuantities = [];
                        }

                        // Crear información de inventario para mostrar
                        let inventoryInfo = "";
                        if (productQuantities && productQuantities.length > 0) {
                            inventoryInfo = "\n\n" + _t("Inventario disponible:") + "\n";
                            for (const product of orderProducts) {
                                const productInfo = productQuantities.find(p => p.product_id === product.id) || { quantity: 0 };
                                inventoryInfo += `- ${product.name}: ${productInfo.quantity || 0} uds. (Pedido: ${product.quantity})\n`;
                            }
                        } else {
                            inventoryInfo = "\n\n" + _t("No se pudo obtener información de inventario");
                        }

                        this.env.services.dialog.add(ConfirmationDialog, {
                            title: _t(`Ubicación ${index + 1} de ${totalLocations}`),
                            body: (location.complete_name || location.name) +
                                  (location.warehouse_id ? `\n${_t("Almacén")}: ${location.warehouse_id[1]}` : '') +
                                  inventoryInfo,
                            confirmLabel: _t('Seleccionar esta ubicación'),
                            cancelLabel: _t('Siguiente ubicación'),
                            confirm: () => {
                                // El usuario seleccionó esta ubicación
                                this.env.services.dialog.add(ConfirmationDialog, {
                                    title: _t('Confirmar selección'),
                                    body: _t('Has seleccionado: ') + (location.complete_name || location.name),
                                    confirmLabel: _t('Confirmar'),
                                    cancelLabel: _t('Cancelar'),
                                    confirm: async () => {
                                        // Preparar líneas para venta estándar
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

                                        // Datos para la venta con ubicación personalizada
                                        const saleData = {
                                            partner_id: partner.id,
                                            order_line: orderLines,
                                            origin: `POS ${this.pos.config?.name || 'Desconocido'}`,
                                            user_id: this.pos.user?.id || false,
                                            auto_validate_picking: true,
                                            custom_location_id: location.id
                                        };

                                        // Si la ubicación tiene un almacén asociado, usamos ese
                                        if (location.warehouse_id) {
                                            saleData.warehouse_id = location.warehouse_id[0];
                                        }

                                        try {
                                            // Crear la venta estándar
                                            const resultado = await this.env.services.orm.call(
                                                'sale.order',
                                                'create_sale_from_pos',
                                                [saleData]
                                            );

                                            // Crear un nuevo pedido vacío
                                            this.pos.add_new_order();

                                            // Eliminar el pedido anterior
                                            const currentOrder = order;
                                            if (this.pos.removeOrder) {
                                                this.pos.removeOrder(currentOrder);
                                            } else if (this.pos.delete_current_order) {
                                                this.pos.delete_current_order();
                                            }

                                            if (this.pos.db && this.pos.db.remove_order) {
                                                this.pos.db.remove_order(currentOrder.uid);
                                            }

                                            this.notification.add(_t("Venta creada correctamente con la ubicación seleccionada"), {
                                                type: "success",
                                            });
                                        } catch (error) {
                                            console.error("Error al crear la venta:", error);
                                            this.notification.add(_t("Error al crear la venta"), {
                                                type: "danger",
                                            });
                                        }
                                    }
                                });
                            },
                            cancel: () => {
                                // Mostrar la siguiente ubicación
                                showLocationDialog(index + 1);
                            }
                        });
                    };

                    // Iniciar con la primera ubicación
                    showLocationDialog(0);

                } catch (error) {
                    console.error("Error detallado:", error);
                    this.notification.add(_t("Error al procesar la operación"), {
                        type: "danger",
                    });
                }
            },
            cancel: () => {
                this.notification.add(_t("Operación cancelada"), {
                    type: "info",
                });
            },
        });
    } catch (error) {
        console.error("Error:", error);
        this.notification.add(_t("Error al mostrar el diálogo"), {
            type: "danger",
        });
    }
}
 });
