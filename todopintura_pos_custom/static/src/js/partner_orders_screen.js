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
            const pedidos = await this.orm.call(
                'sale.order',
                'get_partner_pending_orders',
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

    isSelected(id) {
        return this.state.selectedIds.has(id);
    }

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

            this.props.close();

            const order = this.pos.add_new_order();
            order.set_partner(this.partner);

            for (const orderId of selectedOrders) {
                const saleOrder = await this.pos._getSaleOrder(orderId);
                await this.pos.settleSO(saleOrder);
            }
        } catch (error) {
            console.error("Error al procesar las órdenes:", error);
            this.env.services.notification.add(error.message, { type: "danger" });
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
