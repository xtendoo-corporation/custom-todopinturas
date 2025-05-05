import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";
import { patch } from "@web/core/utils/patch";

// Patch para métodos de instancia
patch(ProductInfoPopup.prototype, {
    setup() {
        super.setup(...arguments);
    },

    _hasMarginsCostsAccessRights() {
        return false;
    }
});

patch(ProductInfoPopup, {
    template: "todopintura_pos_custom.ProductInfoPopup",
});
