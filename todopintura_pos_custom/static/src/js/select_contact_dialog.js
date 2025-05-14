/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class SelectContactDialog extends Component {
    static template = "todopintura_pos_custom.SelectContactDialog";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        contacts: { type: Array },
        close: { type: Function },
        getPayload: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({
            selectedContact: null
        });
        this.title = this.props.title || _t("Seleccionar contacto");
    }

    setSelectedContact(contact) {
        this.state.selectedContact = contact;
    }

    confirm() {
        if (this.state.selectedContact) {
            this.props.close(this.state.selectedContact);
        }
    }

    close() {
        this.props.close(false);
    }
}

registry.category("dialogs").add("SelectContactDialog", SelectContactDialog);
