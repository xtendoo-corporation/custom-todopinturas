/** @odoo-module */
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { patch } from "@web/core/utils/patch";
import { PartnerOrdersScreen } from "./partner_orders_screen";

patch(PartnerLine.prototype, {
    showCreditSales(partner) {
        console.log("showCreditSales", partner);

        this.env.services.dialog.add(PartnerOrdersScreen, {
            partner: partner,
            title: "Pedidos de " + partner.name
        });
    }
});
