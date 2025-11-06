/** @odoo-module */
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

console.log('UbicationButton.js cargado');
export class UbicationButton extends Component {
    static template = "todopintura_pos_custom.UbicationButton";
    changeUbicationLine() {
        console.log("UbicationButton: handler ejecutado correctamente");
        this.env.services.notification.add(_t("Ubicación: handler ejecutado correctamente"), {
            type: "info",
        });
    }
}

registry.category("components").add("todopintura_pos_custom.UbicationButton", UbicationButton);
