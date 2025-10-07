/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";
import { computeComboItems } from "@point_of_sale/app/models/utils/compute_combo_items";

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

        if (combo_parent_lines.length > 0) {
            for (const pLine of combo_parent_lines) {
                const comboData = pLine.combo_line_ids.map((cLine) => {
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
                });

                attributes_prices[pLine.id] = computeComboItems(
                    pLine.product_id,
                    comboData,
                    pricelist,
                    this.models["decimal.precision"].getAll(),
                    this.models["product.template.attribute.value"].getAllBy("id")
                );
            }

            const combo_children_lines = this.lines.filter(
                (line) => line.price_type === "original" && line.combo_parent_id
            );

            combo_children_lines.forEach((line) => {
                if (attributes_prices[line.combo_parent_id.id]) {
                    const priceItem = attributes_prices[line.combo_parent_id.id].find(
                        (item) => item.combo_item_id.id === line.combo_item_id.id
                    );
                    if (priceItem) {
                        line.set_unit_price(priceItem.price_unit);
                    }
                }
            });
        }
    },

    set_partner_option(option) {
        this.partner_option = option;
    },

    get_partner_option() {
        return this.partner_option || false;
    }
});
