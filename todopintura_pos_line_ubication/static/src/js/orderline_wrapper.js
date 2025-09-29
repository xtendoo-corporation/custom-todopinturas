/** @odoo-module */
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { Component } from "@odoo/owl";

export class OrderlineWrapper extends Component {
    static props = {
        line: Object,
        ...Orderline.props,
    };
    setup() {
        const line = { ...this.props.line };
        if (line.product_id && typeof line.product_id !== 'number') {
            line.product_id = Number(line.product_id);
        }
        if (line.order_id && typeof line.order_id !== 'number') {
            line.order_id = Number(line.order_id);
        }
        this.line = line;
        console.log('OrderlineWrapper line corregido:', line);
    }
    get orderlineProps() {
        return {
            ...this.props,
            line: this.line,
        };
    }
    render() {
        return this.env.qweb.render("@point_of_sale/app/components/orderline/orderline", this.orderlineProps);
    }
}

