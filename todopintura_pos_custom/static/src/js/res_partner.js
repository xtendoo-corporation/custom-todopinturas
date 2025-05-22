import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    get searchString() {
        const fields = [
            "name",
            "vat",
            "ref",
        ];
        return fields
            .map((field) => {
                const value = this[field];
                return value ? `${field}:${value}` : "";
            })
            .filter(Boolean)
            .join(" ");
    }
});
