/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

const QUICK_PARTNER_ACTION =
    "todopintura_extend_pos_conventional.action_pos_conventional_quick_partner_wizard";

// "Crear contacto rápido" como primera opción de la rueda dentada del pedido POS.
// Las acciones enlazadas por binding_model_id siempre salen después de "Eliminar",
// por eso se inyecta aquí con groupNumber 0 (los estáticos usan 1 y las de binding 100).
patch(FormController.prototype, {
    get actionMenuItems() {
        const items = super.actionMenuItems;
        if (this.props.resModel !== "pos.order") {
            return items;
        }
        return {
            ...items,
            action: [
                {
                    key: "quick_partner_create",
                    description: _t("Crear contacto rápido"),
                    icon: "fa fa-user-plus",
                    groupNumber: 0,
                    callback: () => this._openQuickPartnerWizard(),
                },
                ...items.action,
            ],
        };
    },

    async _openQuickPartnerWizard() {
        const { resId, resIds } = this.model.root;
        await this.env.services.action.doAction(QUICK_PARTNER_ACTION, {
            additionalContext: { default_order_id: resId },
            // Recargar el pedido al cerrar el diálogo (igual que las acciones de binding)
            onClose: () => this.model.load({ resId, resIds }),
        });
    },
});
