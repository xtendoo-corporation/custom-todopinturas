// odoo/custom/src/custom-todopinturas/todopintura_pos_custom/static/src/js/receipt_order_patch.js
import { patch } from "@web/core/utils/patch";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { _t } from "@web/core/l10n/translation";

patch(ReceiptHeader, {
    get vatText() {
        // Se retorna "CIF: ..." en lugar de "Tax ID: ..."
        return _t("CIF: %(vatId)s", { vatId: this.props.data.company.vat });
    },
});
