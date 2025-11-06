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
import { LocationSelectionDialog } from "@todopintura_pos_line_location/js/location_selection_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { useState, useEffect, onMounted } from "@odoo/owl";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.action = useService("action");
    },

    async clickNewButtonStore() {
        // En Odoo 19, el POS está en this.env.services.pos
        const pos = this.env.services.pos;

        if (!pos) {
            console.error('[ALBARAN] POS no disponible');
            this.notification.add(_t("Error: POS no disponible"), {
                type: "danger",
            });
            return;
        }

        console.log('[ALBARAN] POS encontrado');

        // En Odoo 19, el pedido actual se obtiene con get_order o desde models
        let order = null;

        // Intentar diferentes formas de obtener el pedido
        if (typeof pos.get_order === 'function') {
            order = pos.get_order();
        } else if (pos.selectedOrder) {
            order = pos.selectedOrder;
        } else if (pos.models && pos.models['pos.order']) {
            // Obtener el pedido seleccionado desde el UUID
            const orderUuid = pos.selectedOrderUuid;
            if (orderUuid) {
                order = pos.models['pos.order'].get(orderUuid);
            }
        }

        console.log('[ALBARAN] Order:', order);
        console.log('[ALBARAN] Order properties:', Object.keys(order));

        if (!order) {
            console.error('[ALBARAN] ❌ No hay pedido activo');
            this.notification.add(_t("No hay pedido activo"), {
                type: "warning",
            });
            return;
        }

        console.log('[ALBARAN] ✅ Pedido encontrado');

        // En Odoo 19, las líneas están en order.lines (que es un Proxy)
        // Convertir el Proxy a array
        console.log('[ALBARAN] Obteniendo líneas del pedido...');
        console.log('[ALBARAN] order.lines:', order.lines);

        let orderLines = [];
        if (order.lines) {
            // order.lines es un Proxy/objeto, convertir a array
            orderLines = Object.values(order.lines);
        }

        console.log('[ALBARAN] OrderLines obtenidas:', orderLines);
        console.log('[ALBARAN] Número de líneas:', orderLines.length);

        if (orderLines.length === 0) {
            console.error('[ALBARAN] ❌ No hay productos en el pedido');
            this.notification.add(_t("No hay productos en el pedido actual"), {
                type: "warning",
            });
            return;
        }

        console.log('[ALBARAN] ✅ Pedido tiene', orderLines.length, 'líneas');

        // Obtener el partner - en Odoo 19 está en pos.selectedPartner o en el modelo
        console.log('[ALBARAN] Obteniendo partner...');
        console.log('[ALBARAN] pos.selectedPartner:', pos.selectedPartner);
        console.log('[ALBARAN] order.partner_id:', order.partner_id);
        console.log('[ALBARAN] typeof order.partner_id:', typeof order.partner_id);

        let partner = null;

        // Intentar obtener el partner de diferentes formas
        if (pos.selectedPartner) {
            partner = pos.selectedPartner;
            console.log('[ALBARAN] Partner obtenido desde pos.selectedPartner');
        } else if (order.partner_id) {
            // En Odoo 19, order.partner_id es un Proxy reactivo, puede tener una propiedad 'id'
            let partnerId = null;

            if (typeof order.partner_id === 'number') {
                partnerId = order.partner_id;
            } else if (order.partner_id.id !== undefined) {
                partnerId = order.partner_id.id;
            } else if (Array.isArray(order.partner_id)) {
                partnerId = order.partner_id[0];
            }

            console.log('[ALBARAN] Partner ID extraído:', partnerId);

            if (partnerId && pos.models && pos.models['res.partner']) {
                partner = pos.models['res.partner'].get(partnerId);
                console.log('[ALBARAN] Partner obtenido desde pos.models');
            } else if (partnerId) {
                // Si no está en models, intentar obtenerlo del servidor
                console.log('[ALBARAN] Buscando partner en el servidor...');
                try {
                    const partnerData = await this.orm.call(
                        'res.partner',
                        'read',
                        [[partnerId], ['id', 'name', 'credit_sale', 'credit_location_id']]
                    );
                    if (partnerData && partnerData.length > 0) {
                        partner = partnerData[0];
                        console.log('[ALBARAN] Partner obtenido desde el servidor');
                    }
                } catch (error) {
                    console.error('[ALBARAN] Error al obtener partner del servidor:', error);
                }
            }
        }

        console.log('[ALBARAN] Partner obtenido:', partner);

        if (!partner) {
            console.error('[ALBARAN] ❌ No hay cliente seleccionado');
            this.notification.add(_t("Por favor, selecciona un cliente para el pedido"), {
                type: "warning",
            });
            return;
        }

        console.log('[ALBARAN] ✅ Cliente encontrado');
        console.log('[ALBARAN] Partner:', partner.name);
        console.log('[ALBARAN] Partner ID:', partner.id);
        console.log('[ALBARAN] Partner credit_sale:', partner.credit_sale);
        console.log('[ALBARAN] Número de líneas:', orderLines.length);

        // VALIDACIÓN OBLIGATORIA: El cliente DEBE tener venta a crédito activada
        if (!partner.credit_sale) {
            console.error('[ALBARAN] ❌ Cliente NO tiene venta a crédito activada');
            this.notification.add(
                _t("No se puede crear albarán. El cliente '%s' no tiene activada la venta a crédito.", partner.name),
                { type: "danger" }
            );
            return;
        }

        console.log('[ALBARAN] ✅ Cliente tiene venta a crédito activada');

        // VALIDACIÓN OBLIGATORIA: Si tiene credit_sale, DEBE tener credit_location_id configurado
        console.log('[ALBARAN] Verificando credit_location_id...');
        console.log('[ALBARAN] Partner credit_location_id:', partner.credit_location_id);

        if (!partner.credit_location_id || (Array.isArray(partner.credit_location_id) && partner.credit_location_id.length === 0)) {
            console.error('[ALBARAN] ❌ Cliente tiene venta a crédito pero NO tiene ubicación asignada');
            this.notification.add(
                _t(
                    "No se puede crear albarán.\n\n" +
                    "El cliente '%s' tiene venta a crédito activada pero no tiene configurado el almacén para venta a crédito.\n\n" +
                    "Por favor, configure el campo 'Ubicación Para venta a crédito' en la ficha del cliente.",
                    partner.name
                ),
                {
                    type: "danger",
                    sticky: true
                }
            );
            return;
        }

        console.log('[ALBARAN] ✅ Cliente tiene ubicación de crédito configurada');

        // VALIDACIÓN OBLIGATORIA: Verificar que la ubicación del cliente coincide con la del POS
        try {
            console.log('[ALBARAN] Llamando a check_credit_location_matches_pos...');
            console.log('[ALBARAN] Partner ID:', partner.id);
            console.log('[ALBARAN] POS Config ID:', pos.config.id);

            const result = await this.orm.call(
                "res.partner",
                "check_credit_location_matches_pos",
                [partner.id, pos.config.id]
            );

            console.log('[ALBARAN] Verificación de ubicación:', result);

            if (!result || !result.matches) {
                console.error('[ALBARAN] ❌ Verificación de ubicación FALLÓ');

                let errorMsg = _t("No se puede crear albarán. La ubicación del cliente no coincide con el almacén del POS.");

                if (result && result.partner_location_name && result.pos_location_name) {
                    errorMsg = _t(
                        "No se puede crear albarán.\n\n" +
                        "El cliente '%s' está configurado para el almacén '%s',\n" +
                        "pero el POS está configurado para el almacén '%s'.\n\n" +
                        "Por favor, contacte al administrador.",
                        partner.name,
                        result.partner_location_name,
                        result.pos_location_name
                    );
                } else if (result && result.error) {
                    errorMsg = _t("No se puede crear albarán. %s", result.error);
                }

                this.notification.add(errorMsg, {
                    type: "danger",
                    sticky: true  // Hacer que la notificación persista
                });
                return;
            }

            console.log('[ALBARAN] ✅ Verificación de ubicación PASÓ');
            console.log('[ALBARAN] Ubicación cliente:', result.partner_location_name);
            console.log('[ALBARAN] Ubicación POS:', result.pos_location_name);

        } catch (error) {
            console.error('[ALBARAN] Error al verificar ubicación:', error);
            console.error('[ALBARAN] Error message:', error.message);
            console.error('[ALBARAN] Error data:', error.data);

            let errorMsg = _t("Error al verificar la ubicación del cliente. No se puede crear el albarán.");
            if (error.data && error.data.message) {
                errorMsg = _t("Error al verificar la ubicación: %s", error.data.message);
            }

            this.notification.add(errorMsg, {
                type: "danger",
                sticky: true
            });
            return;
        }

        console.log('[ALBARAN] ========== INICIANDO CREACIÓN DE VENTA ==========');

        try {

            // NUEVO: Detectar cambios de precio
            try {
                console.log("Iniciando verificación de cambios de precio...");
                console.log("Líneas de pedido encontradas:", orderLines.length);

                if (orderLines.length > 0) {
                    const productIds = orderLines.map(line => {
                        // En Odoo 19, el producto puede estar en line.product_id
                        const productId = line.product_id?.id || line.product_id;
                        return productId;
                    }).filter(id => id);

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
                    } else if (pos && pos.config && pos.config.pricelist_id) {
                        if (typeof pos.config.pricelist_id === 'number') {
                            pricelistId = pos.config.pricelist_id;
                        } else if (Array.isArray(pos.config.pricelist_id)) {
                            pricelistId = pos.config.pricelist_id[0];
                        } else if (pos.config.pricelist_id.id) {
                            pricelistId = pos.config.pricelist_id.id;
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
                        // Obtener el producto - en Odoo 19 puede estar como ID o como objeto
                        let product = null;
                        const productId = line.product_id?.id || line.product_id;

                        if (productId && pos.models && pos.models['product.product']) {
                            product = pos.models['product.product'].get(productId);
                        }

                        if (!product) continue;

                        const actualPrice = line.price_unit || 0;

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

            // Obtener el total del pedido
            // En Odoo 19, el total puede estar en order.amount_total o calcular desde las líneas
            let orderTotal = 0;
            if (order.amount_total !== undefined) {
                orderTotal = order.amount_total;
            } else {
                // Calcular total desde las líneas
                orderTotal = orderLines.reduce((sum, line) => {
                    const price = line.price_unit || 0;
                    const qty = line.qty || 0;
                    const discount = line.discount || 0;
                    const subtotal = price * qty * (1 - discount / 100);
                    return sum + subtotal;
                }, 0);
            }
            console.log('[ALBARAN] Total del pedido:', orderTotal);

            console.log('[ALBARAN] Verificando límite de crédito...');
            const creditCheckResult = await this.orm.call(
                'sale.order',
                'check_credit_limit',
                [partner.id, orderTotal]
            );
            console.log('[ALBARAN] Resultado verificación crédito:', creditCheckResult);

            if (creditCheckResult && creditCheckResult.credit_limit_exceeded) {
                console.log('[ALBARAN] ⚠️ Límite de crédito EXCEDIDO');
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
                    console.log('[ALBARAN] ❌ Usuario CANCELÓ por límite de crédito');
                    return; // Cancelar la operación si el usuario no confirma
                }
                console.log('[ALBARAN] ✅ Usuario CONFIRMÓ continuar a pesar del límite');
            } else {
                console.log('[ALBARAN] ✅ Límite de crédito OK o no aplica');
            }

            console.log('[ALBARAN] Preparando líneas de pedido...');
            // Usar orderLines que ya tenemos convertido a array
            console.log('[ALBARAN] Total de líneas:', orderLines.length);

            const orderLinesWithLocation = orderLines.filter(line => {
                return line.locationData &&
                       line.locationData.id !== null &&
                       line.locationData.id !== undefined &&
                       line.locationData.name !== "";
            });
            console.log('[ALBARAN] Líneas con ubicación:', orderLinesWithLocation.length);

            // Crear líneas de pedido (común para ambos casos)
            const allOrderLines = [];
            for (const line of orderLines) {
                // En Odoo 19, acceder a los datos directamente de las propiedades
                let product = null;
                const productId = line.product_id?.id || line.product_id;

                if (productId && pos.models && pos.models['product.product']) {
                    product = pos.models['product.product'].get(productId);
                }

                const quantity = line.qty || 0;
                const price = line.price_unit || 0;
                const discount = line.discount || 0;

                if (!product) {
                    console.warn('[ALBARAN] ⚠️ Línea sin producto, saltando:', line);
                    continue;
                }

                console.log(`[ALBARAN] Procesando línea: ${product.display_name} - Qty: ${quantity} - Price: ${price}`);

                const taxIds = [];
                if (product.taxes_id && product.taxes_id.length) {
                    for (const tax of product.taxes_id) {
                        taxIds.push(typeof tax === 'object' ? tax.id : tax);
                    }
                }

                allOrderLines.push([0, 0, {
                    product_id: product.id,
                    product_uom_qty: quantity,
                    price_unit: price,
                    discount: discount,
                    tax_ids: [[6, 0, taxIds]]  // Corregido: tax_ids en lugar de tax_id
                }]);
            }

            console.log('[ALBARAN] Total líneas procesadas:', allOrderLines.length);


            // Obtener warehouse_id
            let warehouseId = false;
            if (pos.config && pos.config.warehouse_id) {
                warehouseId = Array.isArray(pos.config.warehouse_id)
                    ? pos.config.warehouse_id[0]
                    : pos.config.warehouse_id;
            }
            console.log('[ALBARAN] Warehouse ID:', warehouseId);

            // Obtener el cajero actual del TPV
            let currentCashier = null;
            if (typeof pos.get_cashier === 'function') {
                currentCashier = pos.get_cashier();
            } else if (pos.cashier) {
                currentCashier = pos.cashier;
            }

            let cashierId = false;

            // Enviamos el ID del empleado directamente
            if (currentCashier && currentCashier.id) {
                cashierId = currentCashier.id;  // ID del empleado (no del usuario)
                console.log("[ALBARAN] ID del empleado cajero:", cashierId);
            } else {
                console.warn("[ALBARAN] No se pudo obtener el ID del cajero:", currentCashier);
            }

            // Crear datos base para la venta
            const saleData = {
                partner_id: partner.id,
                order_line: allOrderLines,
                origin: `POS ${pos.config?.name || 'Desconocido'}`,
                auto_validate_picking: true,
                // Enviar ID del empleado
                employee_cashier_id: cashierId  // Renombramos para distinguirlo del user_id
            };
            // Añadir la nota general del pedido POS a los datos de la venta
            if (order.general_note) {
                saleData.general_note = order.general_note;
                console.log("[ALBARAN] Añadiendo nota general a la venta:", order.general_note);
            }
            if (warehouseId) {
                saleData.warehouse_id = warehouseId;
            }

            console.log('[ALBARAN] Datos de venta preparados:', saleData);

            // Guardar referencia al pedido actual
            const currentOrder = order;

            let result;
            // BIFURCACIÓN: Decidir qué método usar según si hay líneas con ubicación o no
            if (orderLinesWithLocation.length === 0) {
                console.log('[ALBARAN] ===== CREANDO VENTA ESTÁNDAR (sin ubicaciones) =====');
                // Llamar al método para venta estándar
                result = await this.orm.call(
                    'sale.order',
                    'create_sale_from_pos',
                    [saleData]
                );
                console.log('[ALBARAN] Resultado venta estándar:', result);
            } else {
                console.log('[ALBARAN] ===== CREANDO VENTA CON MÚLTIPLES ALBARANES (con ubicaciones) =====');
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
                    // En Odoo 19, acceder al product_id directamente
                    const productId = line.product_id?.id || line.product_id;
                    const locationId = line.locationData?.id || null;

                    if (locationId !== null && productId) {
                        // Crear array si no existe para esta ubicación
                        if (!preassignedLocations[locationId]) {
                            preassignedLocations[locationId] = [];
                        }
                        // Añadir el producto a esta ubicación
                        preassignedLocations[locationId].push(productId);
                    }
                });

                console.log('[ALBARAN] Ubicaciones preasignadas:', preassignedLocations);

                // Asignar directamente a los datos de venta sin mostrar diálogo
                saleData.products_by_location = preassignedLocations;

                // Llamar al método para venta con múltiples albaranes
                result = await this.orm.call(
                    'sale.order',
                    'create_sale_with_multiple_pickings_from_pos',
                    [saleData]
                );
                console.log('[ALBARAN] Resultado venta con múltiples albaranes:', result);
            }

            console.log('[ALBARAN] ===== RESULTADO FINAL =====');
            console.log('[ALBARAN] Result completo:', JSON.stringify(result, null, 2));

            // Si result contiene información sobre la venta y los albaranes
            const saleOrderId = result?.id;
            const pickingIds = result?.picking_ids || [];

            console.log('[ALBARAN] Sale Order ID:', saleOrderId);
            console.log('[ALBARAN] Picking IDs:', pickingIds);
            console.log('[ALBARAN] Cantidad de albaranes:', pickingIds.length);

            if (!pickingIds || pickingIds.length === 0) {
                console.error('[ALBARAN] ❌ NO SE GENERARON ALBARANES');
                this.notification.add(_t("Advertencia: No se generaron albaranes"), {
                    type: "warning",
                });
            } else {
                console.log('[ALBARAN] ✅ Albaranes generados correctamente');
            }


            console.log('[ALBARAN] Limpiando el pedido actual...');

            // Estrategia correcta para Odoo 19: eliminar las líneas del pedido
            try {
                console.log('[ALBARAN] Limpiando líneas del pedido actual...');

                // Método 1: Intentar limpiar usando los métodos nativos del pedido
                if (typeof order.clear === 'function') {
                    order.clear();
                    console.log('[ALBARAN] Pedido limpiado con clear()');
                } else if (order.lines) {
                    // Convertir las líneas a array y eliminarlas una por una
                    const linesToDelete = Object.values(order.lines);
                    console.log('[ALBARAN] Eliminando', linesToDelete.length, 'líneas...');

                    for (const line of linesToDelete) {
                        try {
                            // Usar el método de eliminación del pedido si existe
                            if (typeof order.remove_orderline === 'function') {
                                order.remove_orderline(line);
                            } else if (typeof order.removeOrderline === 'function') {
                                order.removeOrderline(line);
                            } else if (line.delete && typeof line.delete === 'function') {
                                line.delete();
                            }
                        } catch (lineError) {
                            console.warn('[ALBARAN] Error al eliminar línea individual:', lineError);
                        }
                    }
                    console.log('[ALBARAN] Líneas eliminadas');
                }

                // NO intentar limpiar el partner, causa error innecesario
                // El pedido queda vacío sin productos, que es suficiente

                console.log('[ALBARAN] ✅ Pedido limpiado correctamente');

            } catch (cleanupError) {
                console.error('[ALBARAN] Error al limpiar pedido:', cleanupError);
                console.warn('[ALBARAN] El pedido no se pudo limpiar automáticamente. El usuario puede eliminarlo manualmente.');
            }

            // Mensaje de éxito
            const successMessage = orderLinesWithLocation.length > 0
                ? _t("Venta creada con albaranes separados por ubicación")
                : _t("Venta estándar creada correctamente");

            console.log('[ALBARAN] Mostrando mensaje de éxito:', successMessage);
            this.notification.add(successMessage, {
                type: "success",
            });

            console.log('[ALBARAN] ===== INTENTANDO IMPRIMIR ALBARANES =====');
            console.log('[ALBARAN] Picking IDs para imprimir:', pickingIds);

            if (!pickingIds || pickingIds.length === 0) {
                console.warn('[ALBARAN] ⚠️ No hay IDs de albaranes para imprimir');
                return;
            }

            const printAction = {
                type: 'ir.actions.act_url',
                url: '/report/pdf/todopintura_pos_delivery_note.report_sale_credit_slip/' + pickingIds.join(','),
                target: 'new'
            };
            console.log('[ALBARAN] Print action:', printAction);

            try {
                console.log('[ALBARAN] Ejecutando acción de impresión...');
                await this.action.doAction(printAction);
                console.log('[ALBARAN] ✅ Acción de impresión ejecutada correctamente');
            } catch (error) {
                console.error("[ALBARAN] ❌ Error al imprimir albaranes:", error);
                this.notification.add(_t("Error al imprimir albaranes"), {
                    type: "warning",
                });
            }

            console.log('[ALBARAN] ========== PROCESO COMPLETADO ==========');
        } catch (error) { // Este catch cierra el try principal del método
            console.error("[ALBARAN] ❌ ERROR GENERAL:", error);
            console.error("[ALBARAN] Error name:", error.name);
            console.error("[ALBARAN] Error message:", error.message);
            console.error("[ALBARAN] Error data:", error.data);
            console.error("[ALBARAN] Error data.message:", error.data?.message);
            console.error("[ALBARAN] Error data.debug:", error.data?.debug);
            console.error("[ALBARAN] Stack trace:", error.stack);

            let errorMessage = _t("Error al crear la venta");
            if (error.data && error.data.message) {
                errorMessage = error.data.message;
            }

            this.notification.add(errorMessage, {
                type: "danger",
            });
        }
    }, // Cierre del método clickNewButtonStore
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
