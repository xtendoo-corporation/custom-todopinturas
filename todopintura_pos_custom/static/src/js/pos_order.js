/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    set_pricelist(pricelist) {
        if (pricelist) {
            this.update({ pricelist_id: pricelist });
        } else {
            this.update({ pricelist_id: false });
        }

        const lines_to_recompute = this.lines.filter(
            (line) =>
                line.price_type === "original" &&
                !(line.combo_line_ids?.length || line.combo_parent_id)
        );

        for (const line of lines_to_recompute) {
            const newPrice = line.product_id.get_price(
                pricelist,
                line.get_quantity(),
                line.get_price_extra()
            );
            line.set_unit_price(newPrice);
        }

        const attributes_prices = {};
        const combo_parent_lines = this.lines.filter(
            (line) => line.price_type === "original" && line.combo_line_ids?.length
        );
        for (const pLine of combo_parent_lines) {
            attributes_prices[pLine.id] = computeComboItems(
                pLine.product_id,
                pLine.combo_line_ids.map((cLine) => {
                    if (cLine.attribute_value_ids) {
                        return {
                            combo_item_id: cLine.combo_item_id,
                            configuration: {
                                attribute_value_ids: cLine.attribute_value_ids,
                            },
                        };
                    } else {
                        return { combo_item_id: cLine.combo_item_id };
                    }
                }),
                pricelist,
                this.models["decimal.precision"].getAll(),
                this.models["product.template.attribute.value"].getAllBy("id")
            );
        }
        const combo_children_lines = this.lines.filter(
            (line) => line.price_type === "original" && line.combo_parent_id
        );
        combo_children_lines.forEach((line) => {
            line.set_unit_price(
                attributes_prices[line.combo_parent_id.id].find(
                    (item) => item.combo_item_id.id === line.combo_item_id.id
                ).price_unit
            );
        });
    },
});
