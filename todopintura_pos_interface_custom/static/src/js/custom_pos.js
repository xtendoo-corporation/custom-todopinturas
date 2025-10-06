/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();

        console.log("Parche ProductScreen en Odoo 19");

        // Inyectamos CSS
        const styleId = "pos-custom-style";
        if (!document.getElementById(styleId)) {
            const style = document.createElement("style");
            style.id = styleId;
            style.textContent = `
                .pos .product-screen .rightpane {
                    display: none !important;
                }
                .pos .product-screen .leftpane {
                    width: 100% !important;
                    max-width: 100% !important;
                }
                .pos .product-screen .orderlines {
                    font-size: 20px !important;
                }
            `;
            document.head.appendChild(style);
        }
    },
});
