/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ClosingPopup } from "@pos_conventional_session_management/js/closing_popup";

/**
 * Al cerrar la caja con pedidos en borrador: avisa y ofrece borrarlos y cerrar.
 * Sin este aviso el cierre fallaba con un mensaje genérico.
 */
export function buildDraftOrdersWarning(draftOrders) {
    const lines = draftOrders.map((order) => {
        const detail = [
            order.partner,
            order.lines ? `${order.lines} ${_t("líneas")}` : "",
            order.amount_total ? `${order.amount_total.toFixed(2)} €` : "",
        ]
            .filter(Boolean)
            .join(" · ");
        return `• ${order.name}${detail ? ` (${detail})` : ""}`;
    });
    return `${_t("Hay pedidos en borrador sin finalizar. Para cerrar la caja hay que finalizarlos o borrarlos.")}\n\n${lines.join("\n")}`;
}

patch(ClosingPopup.prototype, {
    async confirm() {
        const superConfirm = super.confirm.bind(this);
        const sessionId = this.props.sessionId;
        let draftOrders = [];
        try {
            draftOrders = await this.orm.call("pos.session", "get_draft_orders_for_closing", [[sessionId]]);
        } catch (error) {
            console.error("No se pudieron comprobar los pedidos en borrador:", error);
        }
        if (!draftOrders.length) {
            return superConfirm(...arguments);
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Pedidos en borrador"),
            body: buildDraftOrdersWarning(draftOrders),
            confirmLabel: _t("Borrar pedidos en borrador y cerrar caja"),
            cancelLabel: _t("Volver"),
            confirm: async () => {
                try {
                    await this.orm.call("pos.session", "discard_draft_orders_for_closing", [[sessionId]]);
                } catch (error) {
                    this.notification.add(error.data?.message || error.message || _t("No se pudieron borrar los pedidos en borrador."), { type: "danger" });
                    return;
                }
                await superConfirm(...arguments);
            },
            cancel: () => {},
        });
    },
});
