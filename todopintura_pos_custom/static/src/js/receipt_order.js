/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { _t } from "@web/core/l10n/translation";
import { onMounted } from "@odoo/owl";

patch(ReceiptHeader.prototype, {
    get vatText() {
        // Se retorna "CIF: ..." en lugar de "Tax ID: ..."
        return _t("CIF: %(vatId)s", { vatId: this.props.data.company.vat });
    },

    setup() {
        super.setup();
        // En lugar de usar this._super, implementamos directamente
        onMounted(() => {
            console.log("Datos de la compañía:", this.props.data.company);
            console.log("Ciudad:", this.props.data.company.city);
        });
    },
});
