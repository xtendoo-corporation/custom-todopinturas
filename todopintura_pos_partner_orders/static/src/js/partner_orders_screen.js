/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";


export class PartnerOrdersScreen extends Component {
    static template = "todopintura_pos_custom.PartnerOrdersScreen";
    static components = { Dialog };

    static props = {
        ...Dialog.props,
        partner: { type: Object, required: true },
        close: { type: Function, optional: true },
        slots: { type: Array, optional: true },
        title: { type: String, optional: true },
        onProcessOrders: { type: Function, optional: true }
    };

    setup() {
        this.orm = useService("orm");
        this.partner = this.props.partner;
        this.posService = useService("pos");
        this.pos = usePos();

        this.state = useState({
            pedidos: [],
            selectedIds: new Set(),
            loading: true,
            error: false,
            errorMessage: ""
        });

        this.loadOrders();
    }

    async loadOrders() {
    try {
        this.state.loading = true;
        // Modificar para obtener órdenes de venta sin albarán confirmado
        const pedidos = await this.orm.call(
            'sale.order', // Cambia de pos.order a sale.order
            'get_partner_pending_orders', // Nuevo método en el backend
            [this.partner.id]
        );
        console.log("Órdenes de venta pendientes:", pedidos);
        this.state.pedidos = pedidos || [];
        this.state.selectedIds.clear();
    } catch (error) {
        console.error("Error al cargar órdenes de venta:", error);
        this.state.error = true;
        this.state.errorMessage = error.message || "Error desconocido";
    } finally {
        this.state.loading = false;
    }
}

    // Métodos para selección
    isSelected(id) {
        return this.state.selectedIds.has(id);
    }

   // Modifica estos métodos para usar sintaxis de arrow functions
    toggleSelect = (id) => {
        if (this.state.selectedIds.has(id)) {
            this.state.selectedIds.delete(id);
        } else {
            this.state.selectedIds.add(id);
        }
    }

    toggleSelectAll = () => {
        if (this.isAllSelected) {
            this.state.selectedIds.clear();
        } else {
            this.state.pedidos.forEach(pedido => {
                this.state.selectedIds.add(pedido.id);
            });
        }
    }

    get isAllSelected() {
        return this.state.pedidos.length > 0 &&
               this.state.selectedIds.size === this.state.pedidos.length;
    }

    get hasSelectedOrders() {
        return this.state.selectedIds.size > 0;
    }

    get selectedCount() {
        return this.state.selectedIds.size;
    }

    async processSelectedOrders() {
        if (!this.hasSelectedOrders) return;

        try {
            const selectedOrders = Array.from(this.state.selectedIds);
            console.log('[PARTNER ORDERS] Procesando órdenes seleccionadas:', selectedOrders);


            // Obtener el pedido actual - En Odoo 19 se accede de forma diferente
            const pos = this.env.services.pos;

            // Obtener el pedido actual desde el modelo reactivo
            let currentOrder = null;

            if (pos.selectedOrderUuid && pos.models && pos.models['pos.order']) {
                currentOrder = pos.models['pos.order'].get(pos.selectedOrderUuid);
                console.log('[PARTNER ORDERS] Pedido actual obtenido desde selectedOrderUuid');
            }

            if (!currentOrder) {
                console.log('[PARTNER ORDERS] Creando nuevo pedido...');
                // Crear un nuevo pedido
                if (pos.models && pos.models['pos.order']) {
                    currentOrder = pos.models['pos.order'].create({});
                    pos.selectedOrderUuid = currentOrder.uuid;
                    console.log('[PARTNER ORDERS] Nuevo pedido creado:', currentOrder.uuid);
                }
            }

            if (!currentOrder) {
                console.error('[PARTNER ORDERS] No se pudo obtener ni crear un pedido');
                this.env.services.notification.add(
                    'Error: No se pudo crear el pedido en el POS',
                    { type: "danger" }
                );
                return;
            }

            // Establecer el partner en el pedido actual
            if (this.partner) {
                console.log('[PARTNER ORDERS] Estableciendo partner:', this.partner.name);

                // Obtener el partner del modelo reactivo del POS
                let partnerRecord = null;
                if (pos.models && pos.models['res.partner']) {
                    partnerRecord = pos.models['res.partner'].get(this.partner.id);
                }

                if (partnerRecord) {
                    currentOrder.partner_id = partnerRecord;
                    console.log('[PARTNER ORDERS] Partner establecido correctamente');
                } else {
                    console.warn('[PARTNER ORDERS] Partner no encontrado en el modelo POS, usando ID directo');
                    currentOrder.partner_id = this.partner.id;
                }
            }

            // Guardar las IDs de las órdenes de venta en el campo general_customer_note para vincularlas después
            const saleOrderReference = `SALE_ORDERS:${selectedOrders.join(',')}`;
            if (currentOrder.general_customer_note) {
                if (!currentOrder.general_customer_note.includes('SALE_ORDERS:')) {
                    currentOrder.general_customer_note = `${currentOrder.general_customer_note}\n${saleOrderReference}`;
                }
            } else {
                currentOrder.general_customer_note = saleOrderReference;
            }
            console.log('[PARTNER ORDERS] Órdenes de venta guardadas en general_customer_note:', selectedOrders);
            console.log('[PARTNER ORDERS] general_customer_note del pedido:', currentOrder.general_customer_note);

            // Procesar cada orden de venta seleccionada
            for (const orderId of selectedOrders) {
                try {
                    console.log('[PARTNER ORDERS] Procesando orden de venta:', orderId);

                    // Obtener los detalles de la orden de venta
                    const saleOrderData = await this.orm.call(
                        'sale.order',
                        'read',
                        [[orderId], ['order_line', 'name', 'amount_total']]
                    );

                    if (!saleOrderData || saleOrderData.length === 0) {
                        console.warn('[PARTNER ORDERS] No se encontró la orden:', orderId);
                        continue;
                    }

                    const saleOrder = saleOrderData[0];
                    console.log('[PARTNER ORDERS] Datos de la orden:', saleOrder);

                    // Obtener las líneas de la orden
                    const orderLines = await this.orm.call(
                        'sale.order.line',
                        'read',
                        [saleOrder.order_line, ['product_id', 'product_uom_qty', 'price_unit', 'discount', 'tax_ids']]
                    );

                    console.log('[PARTNER ORDERS] Líneas de la orden:', orderLines);

                    // Agregar cada producto al pedido actual del POS
                    for (const line of orderLines) {
                        if (!line.product_id) continue;

                        const productId = Array.isArray(line.product_id) ? line.product_id[0] : line.product_id;

                        // Obtener el producto del modelo
                        let product = null;
                        if (pos.models && pos.models['product.product']) {
                            product = pos.models['product.product'].get(productId);
                        }

                        if (!product) {
                            console.warn('[PARTNER ORDERS] Producto no encontrado en POS:', productId);
                            continue;
                        }

                        console.log('[PARTNER ORDERS] Agregando producto:', product.display_name);

                        // Crear línea de pedido en el POS
                        if (currentOrder && pos.models && pos.models['pos.order.line']) {
                            try {
                                const posLine = pos.models['pos.order.line'].create({
                                    order_id: currentOrder.uuid,
                                    product_id: product,  // Pasar el objeto completo en lugar del ID
                                    qty: line.product_uom_qty || 1,
                                    price_unit: line.price_unit || 0,
                                    discount: line.discount || 0
                                });
                                console.log('[PARTNER ORDERS] Línea creada:', posLine);
                            } catch (lineError) {
                                console.error('[PARTNER ORDERS] Error al crear línea:', lineError);
                            }
                        }
                    }

                    console.log('[PARTNER ORDERS] ✅ Orden procesada:', saleOrder.name);

                } catch (orderError) {
                    console.error('[PARTNER ORDERS] Error al procesar orden', orderId, ':', orderError);
                    console.error('[PARTNER ORDERS] Error message:', orderError.message);
                    console.error('[PARTNER ORDERS] Error data:', orderError.data);

                    let errorMsg = `Error al procesar la orden ${orderId}`;
                    if (orderError.data && orderError.data.message) {
                        errorMsg = `Orden ${orderId}: ${orderError.data.message}`;
                    }

                    this.env.services.notification.add(errorMsg, { type: "warning" });
                }
            }

            this.env.services.notification.add(
                `Se procesaron ${selectedOrders.length} órdenes de venta`,
                { type: "success" }
            );

            // Cerrar este diálogo
            if (this.props.close) {
                this.props.close();
            }

            // Cerrar el diálogo de selección de cliente (PartnerListScreen) si está abierto
            // Navegando directamente a la pantalla de productos
            if (pos.router && typeof pos.router.navigate === 'function') {
                // Navegar a la pantalla de productos
                pos.router.navigate({ screen: 'ProductScreen' });
                console.log('[PARTNER ORDERS] Navegando a ProductScreen');
            } else if (pos.showScreen && typeof pos.showScreen === 'function') {
                // Método alternativo para cambiar de pantalla
                pos.showScreen('ProductScreen');
                console.log('[PARTNER ORDERS] Mostrando ProductScreen (método alternativo)');
            }

        } catch (error) {
            console.error("[PARTNER ORDERS] Error al procesar las órdenes:", error);
            this.env.services.notification.add(
                `Error al procesar las órdenes: ${error.message}`,
                { type: "danger" }
            );
        }
    }

    formatCurrency(amount) {
        return amount.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }) + " €";
    }

    formatDate(dateStr) {
        return new Date(dateStr).toLocaleDateString();
    }

    traducirEstado(state) {
        const estados = {
            'draft': 'Borrador',
            'paid': 'Pagado',
            'done': 'Publicado',
            'invoiced': 'Facturado',
            'cancel': 'Cancelado'
        };
        return estados[state] || state;
    }
}

registry.category("dialogs").add("PartnerOrdersScreen", PartnerOrdersScreen);
