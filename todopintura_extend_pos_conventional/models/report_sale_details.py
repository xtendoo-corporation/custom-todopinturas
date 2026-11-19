# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from collections import OrderedDict

from odoo import api, fields, models


class ReportSaleDetails(models.AbstractModel):
    """Informe de venta diaria: detalle de las ventas agrupado por método de pago,
    cada grupo con su total, además del resumen que trae el informe estándar."""

    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(
        self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs
    ):
        result = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )
        if not session_ids:
            date_start, date_stop = self._get_date_start_and_date_stop(date_start, date_stop)
        orders = self.env["pos.order"].search(
            self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs)
        )
        result["payments_detail"] = self._tp_payments_detail(orders)
        result["payments_detail_total"] = sum(
            group["total"] for group in result["payments_detail"]
        )
        result["payments_detail_count"] = sum(
            group["count"] for group in result["payments_detail"]
        )
        return result

    @api.model
    def _tp_payments_detail(self, orders):
        """[{name, count, total, lines: [{order, date, partner, amount}]}] por método."""
        payments = orders.payment_ids.sorted(
            lambda p: (
                p.payment_method_id.sequence,
                p.payment_method_id.name or "",
                p.payment_date or fields.Datetime.now(),
                p.id,
            )
        )
        groups = OrderedDict()
        for payment in payments:
            method = payment.payment_method_id
            group = groups.setdefault(
                method.id,
                {"id": method.id, "name": method.name, "count": 0, "total": 0.0, "lines": []},
            )
            when = (
                fields.Datetime.context_timestamp(self, payment.payment_date)
                if payment.payment_date
                else False
            )
            group["lines"].append(
                {
                    "order": payment.pos_order_id.pos_reference
                    or payment.pos_order_id.name,
                    "date": when.strftime("%d/%m %H:%M") if when else "",
                    "partner": payment.pos_order_id.partner_id.name or "",
                    "amount": payment.amount,
                }
            )
            group["count"] += 1
            group["total"] += payment.amount
        return list(groups.values())
