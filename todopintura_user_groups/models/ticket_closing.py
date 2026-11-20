# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime, time, timedelta

import pytz

from odoo import _, fields, models

NO_WAREHOUSE = "SIN ALMACÉN"


class TicketClosing(models.TransientModel):
    """Listado cierre de tickets: todos los tickets y facturas hechos en un día.

    Una sección por tienda (almacén) con una línea por ticket o factura (número,
    fecha, cliente e importe) y el total de tickets al final.
    """

    _name = "todopintura.ticket.closing"
    _description = "Listado cierre de tickets"

    date = fields.Date(
        string="Día", required=True, default=fields.Date.context_today
    )
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "todopintura_tc_warehouse_rel",
        "closing_id",
        "warehouse_id",
        string="Almacenes",
        help="Vacío = todos (los usuarios con almacenes asignados solo ven los suyos).",
    )

    # ---- datos --------------------------------------------------------------------
    def _day_bounds(self):
        """Inicio y fin del día (hora del usuario) en UTC, como guarda Odoo las fechas."""
        self.ensure_one()
        tz = pytz.timezone(self.env.user.tz or "UTC")
        start = tz.localize(datetime.combine(self.date, time.min))
        end = start + timedelta(days=1)
        to_utc = lambda value: value.astimezone(pytz.utc).replace(tzinfo=None)  # noqa: E731
        return to_utc(start), to_utc(end)

    def _allowed_warehouses(self):
        self.ensure_one()
        warehouses = self.warehouse_ids
        allowed = self.env.user.allowed_warehouse_ids
        if allowed:
            warehouses = warehouses & allowed if warehouses else allowed
        return warehouses

    def _customer(self, partner):
        return (partner.ref or "", partner.name or "")

    def _get_tickets(self, start, end):
        orders = self.env["pos.order"].sudo().search(
            [
                ("date_order", ">=", start),
                ("date_order", "<", end),
                ("state", "in", ("paid", "done", "invoiced")),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        rows = []
        for order in orders:
            warehouse = order.config_id.picking_type_id.warehouse_id
            code, name = self._customer(order.partner_id)
            rows.append(
                {
                    "kind": "ticket",
                    "warehouse": warehouse,
                    "number": order.pos_reference or order.name,
                    "when": order.date_order,
                    "customer_code": code,
                    "customer_name": name,
                    "amount": order.amount_total,
                }
            )
        return rows

    def _get_invoices(self):
        """Facturas del día que no vienen de un ticket (las que sí, ya salen como ticket)."""
        moves = self.env["account.move"].sudo().search(
            [
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("state", "=", "posted"),
                ("invoice_date", "=", self.date),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        from_tickets = set(
            self.env["pos.order"].sudo().search([("account_move", "in", moves.ids)]).account_move.ids
        )
        rows = []
        for move in moves.filtered(lambda m: m.id not in from_tickets):
            orders = move.invoice_line_ids.sale_line_ids.order_id
            code, name = self._customer(move.partner_id)
            sign = -1 if move.move_type == "out_refund" else 1
            rows.append(
                {
                    "kind": "invoice",
                    "warehouse": orders[:1].warehouse_id,
                    "number": move.name,
                    "when": datetime.combine(move.invoice_date, time.min),
                    "customer_code": code,
                    "customer_name": name,
                    "amount": sign * abs(move.amount_total),
                }
            )
        return rows

    def _get_data(self):
        """[{name, rows, tickets_total, invoices_total, total}] por tienda, más el total general."""
        self.ensure_one()
        start, end = self._day_bounds()
        rows = self._get_tickets(start, end) + self._get_invoices()
        warehouses = self._allowed_warehouses()
        if warehouses:
            rows = [r for r in rows if r["warehouse"] in warehouses]
        stores = {}
        for row in rows:
            key = row["warehouse"].id or 0
            store = stores.setdefault(
                key,
                {
                    "name": (row["warehouse"].name or NO_WAREHOUSE).upper(),
                    "rows": [],
                },
            )
            store["rows"].append(row)
        result = []
        for store in sorted(stores.values(), key=lambda s: s["name"]):
            store["rows"].sort(key=lambda r: (r["kind"] != "ticket", r["when"], r["number"]))
            store["tickets_total"] = sum(r["amount"] for r in store["rows"] if r["kind"] == "ticket")
            store["invoices_total"] = sum(r["amount"] for r in store["rows"] if r["kind"] == "invoice")
            store["total"] = store["tickets_total"] + store["invoices_total"]
            store["has_invoices"] = any(r["kind"] == "invoice" for r in store["rows"])
            result.append(store)
        return {
            "stores": result,
            "tickets_total": sum(s["tickets_total"] for s in result),
            "invoices_total": sum(s["invoices_total"] for s in result),
            "total": sum(s["total"] for s in result),
            "has_invoices": any(s["has_invoices"] for s in result),
            "count": sum(len(s["rows"]) for s in result),
        }

    def _format_date(self, value):
        """dd/mm/yy en hora del usuario."""
        if isinstance(value, datetime):
            value = fields.Datetime.context_timestamp(self, value)
        return value.strftime("%d/%m/%y")

    # ---- acciones -------------------------------------------------------------------
    def action_print(self):
        self.ensure_one()
        return self.env.ref("todopintura_user_groups.action_report_ticket_closing").report_action(self)
