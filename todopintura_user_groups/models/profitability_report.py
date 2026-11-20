# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import io

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

LOW_MARGIN = 30.0  # por debajo de este % de beneficio se marca con «**»
DOC_DELIVERY_NOTE = "ALBARAN"  # pedido entregado y sin facturar
DOC_CASH = "Contado"  # tickets y facturas (A4 o simplificadas)

COLUMNS = [
    # (cabecera, campo, tipo, ancho)
    ("ALMACEN", "warehouse_name", "text", 24),
    ("COMERCIAL", "user_name", "text", 20),
    ("ARTICULO", "product_code", "text", 14),
    ("DESCRIPCION", "product_name", "text", 40),
    ("NUMERO", "partner_code", "text", 11),
    ("NOMBRE DE CLIENTE", "partner_name", "text", 34),
    ("FECHA", "date", "date", 11),
    ("NUM.", "number", "text", 16),
    ("CANTIDAD", "qty", "number", 10),
    ("P.COSTO", "cost_unit", "number", 10),
    ("P.V.P.", "price_unit", "number", 10),
    ("BENEFIC.", "profit", "number", 11),
    (" % Bº", "profit_percent", "number", 8),
    ("TIPO", "flag", "text", 6),
    ("DOCUMENTO", "doc_type", "text", 12),
]


class ProfitabilityReport(models.TransientModel):
    """Listado de rentabilidad por línea, exportable a Excel.

    Una fila por línea de venta entregada: tickets y facturas (A4 o simplificadas) como
    «Contado» y pedidos entregados sin facturar como «ALBARAN». Marca con «**» las
    líneas con menos de un 30 % de beneficio.
    """

    _name = "todopintura.profitability.report"
    _description = "Listado de rentabilidad"

    date_from = fields.Date(
        string="Fecha de inicio",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="Fecha de fin", required=True, default=fields.Date.context_today
    )
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "todopintura_profit_warehouse_rel",
        "report_id",
        "warehouse_id",
        string="Almacenes",
        help="Vacío = todos los almacenes (los usuarios con almacenes asignados solo ven los suyos).",
    )
    line_ids = fields.One2many("todopintura.profitability.report.line", "report_id")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for report in self:
            if report.date_from > report.date_to:
                raise ValidationError(_("La fecha de inicio no puede ser posterior a la de fin."))

    # ---- datos --------------------------------------------------------------------
    def _get_warehouses(self):
        self.ensure_one()
        warehouses = self.warehouse_ids
        allowed = self.env.user.allowed_warehouse_ids
        if allowed:
            warehouses = warehouses & allowed if warehouses else allowed
        return warehouses

    def _query(self):
        """SQL de las líneas entregadas: tickets, pedidos de venta y facturas sueltas."""
        cost = "COALESCE((pp.standard_price ->> (%(company)s)::text)::numeric, 0)"
        pos_cost = cost % {"company": "o.company_id"}
        sale_cost = cost % {"company": "so.company_id"}
        inv_cost = cost % {"company": "m.company_id"}
        local = "AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s"
        return f"""
            SELECT t.* FROM (
                -- Tickets del TPV (pagados o contabilizados) con todo entregado
                SELECT spt.warehouse_id AS warehouse_id,
                       o.user_id AS user_id,
                       l.product_id AS product_id,
                       o.partner_id AS partner_id,
                       (o.date_order {local})::date AS date,
                       COALESCE(o.pos_reference, o.name) AS number,
                       l.qty AS qty,
                       l.price_subtotal AS amount,
                       l.qty * {pos_cost} AS cost,
                       '{DOC_CASH}' AS doc_type
                  FROM pos_order_line l
                  JOIN pos_order o ON o.id = l.order_id
                  JOIN pos_session s ON s.id = o.session_id
                  JOIN pos_config c ON c.id = s.config_id
                  LEFT JOIN stock_picking_type spt ON spt.id = c.picking_type_id
                  JOIN product_product pp ON pp.id = l.product_id
                 WHERE o.state IN ('paid', 'done', 'invoiced')
                   AND o.company_id IN %(companies)s
                   AND NOT EXISTS (
                        SELECT 1 FROM stock_picking sp
                         WHERE sp.pos_order_id = o.id AND sp.state NOT IN ('done', 'cancel'))

                UNION ALL

                -- Pedidos de venta entregados: sin facturar «ALBARAN», facturados «Contado»
                SELECT so.warehouse_id AS warehouse_id,
                       so.user_id AS user_id,
                       sol.product_id AS product_id,
                       so.partner_id AS partner_id,
                       (COALESCE(
                            (SELECT max(sm.date) FROM stock_move sm
                              WHERE sm.sale_line_id = sol.id AND sm.state = 'done'),
                            so.date_order) {local})::date AS date,
                       so.name AS number,
                       sol.product_uom_qty AS qty,
                       sol.price_subtotal AS amount,
                       sol.product_uom_qty * {sale_cost} AS cost,
                       CASE WHEN so.invoice_status = 'invoiced'
                            THEN '{DOC_CASH}' ELSE '{DOC_DELIVERY_NOTE}' END AS doc_type
                  FROM sale_order_line sol
                  JOIN sale_order so ON so.id = sol.order_id
                  JOIN product_product pp ON pp.id = sol.product_id
                 WHERE so.state = 'sale'
                   AND sol.display_type IS NULL
                   AND so.delivery_status = 'full'
                   AND so.company_id IN %(companies)s

                UNION ALL

                -- Facturas A4 / simplificadas que no vienen de un ticket ni de un pedido
                SELECT NULL::integer AS warehouse_id,
                       m.invoice_user_id AS user_id,
                       aml.product_id AS product_id,
                       m.partner_id AS partner_id,
                       m.invoice_date AS date,
                       m.name AS number,
                       CASE WHEN m.move_type = 'out_refund' THEN -aml.quantity
                            ELSE aml.quantity END AS qty,
                       -aml.balance AS amount,
                       CASE WHEN m.move_type = 'out_refund' THEN -aml.quantity
                            ELSE aml.quantity END * {inv_cost} AS cost,
                       '{DOC_CASH}' AS doc_type
                  FROM account_move_line aml
                  JOIN account_move m ON m.id = aml.move_id
                  JOIN product_product pp ON pp.id = aml.product_id
                 WHERE m.move_type IN ('out_invoice', 'out_refund')
                   AND m.state = 'posted'
                   AND aml.display_type = 'product'
                   AND m.company_id IN %(companies)s
                   AND NOT EXISTS (SELECT 1 FROM pos_order po WHERE po.account_move = m.id)
                   AND NOT EXISTS (
                        SELECT 1
                          FROM sale_order_line_invoice_rel rel
                          JOIN account_move_line l2 ON l2.id = rel.invoice_line_id
                         WHERE l2.move_id = m.id)
            ) t
             WHERE t.date BETWEEN %(date_from)s AND %(date_to)s
               AND (%(any_warehouse)s OR t.warehouse_id IN %(warehouses)s)
             ORDER BY t.date, t.number, t.product_id
        """

    def _get_rows(self):
        """Filas del listado: una por línea, con precios unitarios, beneficio y marca «**»."""
        self.ensure_one()
        warehouses = self._get_warehouses()
        self.env.flush_all()  # la consulta SQL debe ver lo último escrito por el ORM
        self.env.cr.execute(
            self._query(),
            {
                "tz": self.env.user.tz or "UTC",
                "companies": tuple(self.env.companies.ids),
                "date_from": self.date_from,
                "date_to": self.date_to,
                "any_warehouse": not warehouses,
                "warehouses": tuple(warehouses.ids) or (0,),
            },
        )
        data = self.env.cr.dictfetchall()
        products = self.env["product.product"].sudo().browse({r["product_id"] for r in data})
        partners = self.env["res.partner"].sudo().browse({r["partner_id"] for r in data if r["partner_id"]})
        users = self.env["res.users"].sudo().browse({r["user_id"] for r in data if r["user_id"]})
        wh_names = {
            w.id: w.name
            for w in self.env["stock.warehouse"].sudo().browse({r["warehouse_id"] for r in data if r["warehouse_id"]})
        }
        product_by_id = {p.id: p for p in products}
        partner_by_id = {p.id: p for p in partners}
        user_by_id = {u.id: u for u in users}
        rows = []
        for r in data:
            qty, amount, cost = r["qty"] or 0.0, r["amount"] or 0.0, r["cost"] or 0.0
            product = product_by_id[r["product_id"]]
            partner = partner_by_id.get(r["partner_id"])
            profit = amount - cost
            percent = profit / amount * 100.0 if amount else 0.0
            rows.append(
                {
                    "warehouse_name": wh_names.get(r["warehouse_id"], ""),
                    "user_name": user_by_id[r["user_id"]].name if r["user_id"] in user_by_id else "",
                    "product_code": product.default_code or "",
                    "product_name": product.name or "",
                    "partner_code": (partner.ref or "") if partner else "",
                    "partner_name": (partner.name or "") if partner else "",
                    "date": r["date"],
                    "number": r["number"] or "",
                    "qty": qty,
                    "cost_unit": round(cost / qty, 2) if qty else 0.0,
                    "price_unit": round(amount / qty, 2) if qty else 0.0,
                    "profit": round(profit, 2),
                    "profit_percent": round(percent, 2),
                    "flag": "**" if percent < LOW_MARGIN else "",  # con el % sin redondear
                    "doc_type": r["doc_type"],
                }
            )
        return rows

    # ---- acciones ----------------------------------------------------------------------
    def action_show(self):
        """Calcula el listado y lo abre en modo lista."""
        self.ensure_one()
        self.line_ids.sudo().unlink()
        Line = self.env["todopintura.profitability.report.line"].sudo()
        Line.create(
            [dict(row, report_id=self.id, sequence=i) for i, row in enumerate(self._get_rows(), start=1)]
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Listado de rentabilidad"),
            "res_model": "todopintura.profitability.report.line",
            "view_mode": "list",
            "views": [(self.env.ref("todopintura_user_groups.view_profitability_report_line_list").id, "list")],
            "search_view_id": self.env.ref("todopintura_user_groups.view_profitability_report_line_search").id,
            "domain": [("report_id", "=", self.id)],
            "context": {"create": False, "edit": False, "delete": False},
            "target": "current",
        }

    def action_export_xlsx(self):
        """Descarga el listado en Excel con las columnas del listado de rentabilidad."""
        self.ensure_one()
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"rentabilidad_{self.date_from}_{self.date_to}.xlsx",
                "datas": base64.b64encode(self._build_xlsx(self._get_rows())),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    @staticmethod
    def _build_xlsx(rows):
        import xlsxwriter

        stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(stream, {"in_memory": True})
        sheet = workbook.add_worksheet("excel-rent")
        head = workbook.add_format({"bold": True, "bg_color": "#E9ECEF", "border": 1})
        number = workbook.add_format({"num_format": "#,##0.00"})
        date = workbook.add_format({"num_format": "dd/mm/yy"})
        for col, (label, _field, _kind, width) in enumerate(COLUMNS):
            sheet.write(0, col, label, head)
            sheet.set_column(col, col, width)
        for index, row in enumerate(rows, start=1):
            for col, (_label, field, kind, _width) in enumerate(COLUMNS):
                value = row[field]
                if kind == "number":
                    sheet.write_number(index, col, value or 0.0, number)
                elif kind == "date":
                    sheet.write_datetime(index, col, fields.Datetime.to_datetime(value), date)
                else:
                    sheet.write_string(index, col, value or "")
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, max(len(rows), 1), len(COLUMNS) - 1)
        workbook.close()
        return stream.getvalue()


class ProfitabilityReportLine(models.TransientModel):
    _name = "todopintura.profitability.report.line"
    _description = "Línea del listado de rentabilidad"
    _order = "report_id, sequence"

    report_id = fields.Many2one("todopintura.profitability.report", ondelete="cascade", index=True)
    sequence = fields.Integer()
    warehouse_name = fields.Char(string="Almacén")
    user_name = fields.Char(string="Comercial")
    product_code = fields.Char(string="Artículo")
    product_name = fields.Char(string="Descripción")
    partner_code = fields.Char(string="Nº cliente")
    partner_name = fields.Char(string="Cliente")
    date = fields.Date(string="Fecha")
    number = fields.Char(string="Núm.")
    qty = fields.Float(string="Cantidad", digits="Product Unit", aggregator="sum")
    cost_unit = fields.Float(string="P. costo", digits="Product Price", aggregator=False)
    price_unit = fields.Float(string="P.V.P.", digits="Product Price", aggregator=False)
    profit = fields.Float(string="Benefic.", digits="Product Price", aggregator="sum")
    profit_percent = fields.Float(string="% Bº", digits=(12, 2), aggregator=False)
    flag = fields.Char(string="Tipo")
    doc_type = fields.Char(string="Documento")
