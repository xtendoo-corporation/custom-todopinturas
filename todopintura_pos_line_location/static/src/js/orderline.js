/** @odoo-module */
import { OrderlineWrapper } from "./orderline_wrapper";
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline, {
  setup() {
    return new OrderlineWrapper(this.props);
  },
});
