/** @odoo-module */

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    async getNewPartners() {
        console.log("Buscando contactos...");
        console.log("Offset actual:", this.state.currentOffset);
        let domain = [];
        const limit = 100000;

        if (this.state.query) {
            domain = [["name", "ilike", this.state.query + "%"]];
        }

        const result = await this.pos.data.searchRead("res.partner", domain, [], {
            limit: limit,
            offset: this.state.currentOffset,
        });
        console.log("Contactos encontrados:", result.length);
        return result;
    }
});
