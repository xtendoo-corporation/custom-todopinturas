/** @odoo-module */

import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { Component, markup } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { LocationLineDialog } from "./location_line_dialog";
import { LocationSelectionDialog } from "@todopintura_pos_line_ubication/js/location_selection_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
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
        // En Odoo 19 y Owl, el POS se accede por this.env.pos
        const pos = this.env?.pos || this.pos;
        const order = pos && pos.get_order ? pos.get_order() : null;
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
                [partner.id, pos.config.id]
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
        // En Odoo 19 y Owl, el POS se accede por this.env.pos
        const pos = this.env?.pos || this.pos;
        const order = pos && pos.get_order ? pos.get_order() : null;

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

            // NUEVO: Detectar cambios de precio
            try {
                console.log("Iniciando verificación de cambios de precio...");
                const orderLines = order.get_orderlines();
                console.log("Líneas de pedido encontradas:", orderLines.length);

                if (orderLines.length > 0) {
                    const partner = order.get_partner();
                    const productIds = orderLines.map(line => line.get_product().id);

                    // Obtener la lista de precios del cliente
                    let pricelistId = null;
                    if (partner && partner.property_product_pricelist) {
                        if (typeof partner.property_product_pricelist === 'number') {
                            pricelistId = partner.property_product_pricelist;
                        } else if (Array.isArray(partner.property_product_pricelist)) {
                            pricelistId = partner.property_product_pricelist[0];
                        } else if (partner.property_product_pricelist.id) {
                            pricelistId = partner.property_product_pricelist.id;
                        }
                        console.log("Usando lista de precios del cliente (ID):", pricelistId);
                    } else if (this.pos && this.pos.config && this.pos.config.pricelist_id) {
                        if (typeof this.pos.config.pricelist_id === 'number') {
                            pricelistId = this.pos.config.pricelist_id;
                        } else if (Array.isArray(this.pos.config.pricelist_id)) {
                            pricelistId = this.pos.config.pricelist_id[0];
                        } else if (this.pos.config.pricelist_id.id) {
                            pricelistId = this.pos.config.pricelist_id.id;
                        }
                        console.log("Usando lista de precios del POS (ID):", pricelistId);
                    }

                    // Obtener precios según tarifa del cliente
                    let partnerPrices = {};
                    try {
                        partnerPrices = await this.orm.call(
                            'product.product',
                            'get_partner_prices',
                            [productIds, partner.id, pricelistId]
                        );
                        console.log("Precios según tarifa obtenidos:", partnerPrices);
                    } catch (priceError) {
                        console.warn("Error al obtener precios según tarifa:", priceError);
                    }

                    // Registrar cambios de precio uno por uno
                    for (const line of orderLines) {
                        const product = line.get_product();
                        const actualPrice = line.get_unit_price();

                        // Usar precio de tarifa si existe, o precio base como fallback
                        const expectedPrice = partnerPrices[product.id] || product.lst_price;

                        console.log(`Producto ${product.id} (${product.display_name}): Precio actual ${actualPrice} vs Esperado ${expectedPrice}`);

                        // Solo procesar líneas con diferencia de precio
                        if (Math.abs(actualPrice - expectedPrice) > 0.01) {
                            console.log(`⚠️ Diferencia de precio en ${product.display_name}: ${expectedPrice} → ${actualPrice}`);

                            // Datos mínimos
                            const priceData = {
                                product_id: product.id,
                                original_price: expectedPrice,
                                new_price: actualPrice,
                                order_reference: order.name || 'Sin referencia'
                            };

                            // Registrar cambio
                            try {
                                const result = await this.orm.call(
                                    'pos.price.change.log',
                                    'create',
                                    [[priceData]]
                                );
                                console.log(`✅ Cambio registrado para producto ${product.id}: ${result}`);
                            } catch (lineError) {
                                console.error(`Error al registrar cambio para producto ${product.id}:`, lineError);
                            }
                        }
                    }
                }
                console.log("Verificación de precios completada");
            } catch (priceError) {
                console.error("❌ Error general en verificación de precios:", priceError);
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
            pos.add_new_order();
            if (pos.removeOrder) {
                pos.removeOrder(order);
            } else if (pos.delete_current_order) {
                pos.delete_current_order();
            }

            // Mensaje de éxito
            const successMessage = orderLinesWithLocation.length > 0
                ? _t("Venta creada con albaranes separados por ubicación")
                : _t("Venta estándar creada correctamente");

            this.notification.add(successMessage, {
                type: "success",
            });

            const printAction = {
                type: 'ir.actions.act_url',
                url: '/report/pdf/todopintura_pos_custom.report_sale_credit_slip/' + pickingIds.join(','),
                target: 'new'
            };
            try {
                await this.action.doAction(printAction);
            } catch (error) {
                console.error("Error al imprimir albaranes:", error);
                this.notification.add(_t("Error al imprimir albaranes"), {
                    type: "warning",
                });
            }
        } catch (error) { // Este catch cierra el try principal del método
            console.error("Error al crear la venta:", error);
            this.notification.add(_t("Error al crear la venta"), {
                type: "danger",
            });
        }
    } // Cierre del método clickNewButtonStore
});

patch(ProductScreen.prototype, {
    setup() {
        if (super.setup) {
            super.setup();
        }
        // Eliminado: this.on('change-ubication-line', this, this._onChangeUbicationLine);
        // Si necesitas escuchar eventos personalizados, usa posbus o useBus.
    },
    async _onChangeUbicationLine() {
        const pos = this.env.pos;
        const order = pos && typeof pos.get_order === 'function' ? pos.get_order() : null;
        if (!order) {
            this.env.services.notification.add(_t("No hay pedido activo."), { type: "warning" });
            return;
        }
        const selectedLine = order.get_selected_orderline ? order.get_selected_orderline() : null;
        if (!selectedLine) {
            this.env.services.notification.add(_t("Selecciona una línea de pedido primero."), { type: "warning" });
            return;
        }
        let locations = await this.env.services.orm.call(
            'stock.location',
            'search_read',
            [[['usage', '=', 'internal'], ['active', '=', true]]],
            {fields: ['id', 'name', 'complete_name', 'warehouse_id']}
        );
        if (!locations || locations.length === 0) {
            this.env.services.notification.add(_t("No se encontraron ubicaciones disponibles."), { type: "warning" });
            return;
        }
        const inventoryData = {};
        const selectedLocation = await new Promise(resolve => {
            this.env.services.dialog.add(LocationLineDialog, {
                title: _t("Seleccionar Ubicación"),
                locations: locations,
                inventoryData: inventoryData,
                confirm: (location) => resolve(location),
                close: () => resolve(null)
            });
        });
        if (selectedLocation) {
            selectedLine.set_location(
                selectedLocation.id ? Number(selectedLocation.id) : null,
                selectedLocation.name ? String(selectedLocation.name) : ""
            );
            this.env.services.notification.add(_t("Ubicación actualizada correctamente."), { type: "success" });
        }
    },
});
