/** @odoo-module */

import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";

export class CouponAndAssignedPeopleDialog extends Dialog {
    static template = "todopintura_pos_custom.CouponAndAssignedPeopleDialog";
    static components = { Dialog }; // Añade esta línea
    static props = {
        ...Dialog.props,
        partner: Object,
        confirm: Function,
        close: Function,
        slots: { type: Array, optional: true },
    };

    setup() {
        super.setup();
        this.state = useState({
            option: "coupon" // valor por defecto
        });
    }

    selectOption(option) {
        this.state.option = option;
    }

    onClickConfirm() {
        this.props.confirm(this.state.option);
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }
}

registry.category("dialogs").add("couponAndAssignedPeopleDialog", CouponAndAssignedPeopleDialog);
