import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    get searchString() {
        const fields = [
            "name",
        ];
        return this.name || "";
    }
});
