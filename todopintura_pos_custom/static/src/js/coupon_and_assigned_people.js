/** @odoo-module */

import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";

export class CouponAndAssignedPeopleDialog extends Dialog {
    static template = "todopintura_pos_custom.CouponAndAssignedPeopleDialog";
    static components = { Dialog };
    static props = {
        ...Dialog.props,
        partner: Object,
        confirm: Function,
        close: Function,
        slots: { type: Array, optional: true },
        assignedPeopleInfo: { type: [String, { value: false }], optional: true },
    };

    setup() {
        super.setup();
    }

    onClickConfirm() {
        this.props.confirm('assigned_people');
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }

    get assignedPeopleText() {
        return this.props.assignedPeopleInfo || '';
    }

    get hasVoucher() {
        return this.props.partner && this.props.partner.voucher === true;
    }

    get voucherText() {
        if (this.hasVoucher) {
            return _t('Este cliente tiene vales disponibles para usar en sus compras');
        }
        return '';
    }
}

registry.category("dialogs").add("couponAndAssignedPeopleDialog", CouponAndAssignedPeopleDialog);
