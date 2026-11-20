# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import io

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

COST_GROUP = "todopintura_user_groups.group_cost_viewer"


class CustomerItemReport(models.TransientModel):
    """Listado acumulado de artículos por cliente.

    Se pregunta qué clientes, proveedores, fechas y almacenes y se muestra en lista:
    una fila por cliente (con sus totales) y debajo una por artículo, con precios de
    venta y coste por unidad, margen por unidad y los totales acumulados.
    """

    _name = "todopintura.customer.item.report"
    _description = "Listado acumulado de artículos por cliente"

    partner_ids = fields.Many2many(
        "res.partner",
        "todopintura_cir_partner_rel",
        "report_id",
        "partner_id",
        string="Clientes",
        help="Vacío = todos los clientes.",
    )
    supplier_ids = fields.Many2many(
        "res.partner",
        "todopintura_cir_supplier_rel",
        "report_id",
        "partner_id",
        string="Proveedores",
        help="Solo artículos de estos proveedores. Vacío = todos.",
    )
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "todopintura_cir_warehouse_rel",
        "report_id",
        "warehouse_id",
        string="Almacenes",
        help="Vacío = todos los almacenes (los usuarios con almacenes asignados solo ven los suyos).",
    )
    date_from = fields.Date(
        string="Desde",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="Hasta", required=True, default=fields.Date.context_today
    )
    line_ids = fields.One2many("todopintura.customer.item.report.line", "report_id")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for report in self:
            if report.date_from > report.date_to:
                raise ValidationError(_("La fecha «Desde» no puede ser posterior a «Hasta»."))

    # ---- datos --------------------------------------------------------------------
    def _get_domain(self):
        self.ensure_one()
        domain = [("date", ">=", self.date_from), ("date", "<=", self.date_to)]
        if self.partner_ids:
            domain.append(("partner_id", "child_of", self.partner_ids.ids))
        if self.supplier_ids:
            domain.append(
                (
                    "product_id.product_tmpl_id.seller_ids.partner_id",
                    "in",
                    self.supplier_ids.ids,
                )
            )
        warehouses = self.warehouse_ids
        allowed = self.env.user.allowed_warehouse_ids
        if allowed:
            warehouses = warehouses & allowed if warehouses else allowed
        if warehouses:
            domain.append(("warehouse_id", "in", warehouses.ids))
        return domain

    def _get_rows(self):
        """Filas del listado: [{kind, code, name, qty, price_unit, ...}] ordenadas."""
        self.ensure_one()
        Report = self.env["todopintura.sales.report"].sudo()
        grouped = Report._read_group(
            self._get_domain(),
            groupby=["partner_id", "product_id"],
            aggregates=["qty:sum", "amount:sum", "cost:sum"],
        )
        customers = {}
        for partner, product, qty, amount, cost in grouped:
            if not product:
                continue
            commercial = partner.commercial_partner_id if partner else partner
            data = customers.setdefault(commercial.id, {"partner": commercial, "items": {}})
            item = data["items"].setdefault(product.id, [product, 0.0, 0.0, 0.0])
            item[1] += qty
            item[2] += amount
            item[3] += cost

        rows = []
        ordered = sorted(
            customers.values(),
            key=lambda c: (c["partner"].name or "~").lower() if c["partner"] else "~",
        )
        for data in ordered:
            partner = data["partner"]
            items = sorted(
                data["items"].values(),
                key=lambda i: (i[0].default_code or "~", i[0].name or ""),
            )
            sums = [sum(i[k] for i in items) for k in (1, 2, 3)]
            rows.append(
                self._build_row(
                    "customer",
                    partner.ref or "",
                    partner.name or _("Sin cliente"),
                    sums[0],
                    sums[1],
                    sums[2],
                )
            )
            for product, qty, amount, cost in items:
                rows.append(
                    self._build_row(
                        "item",
                        product.default_code or "",
                        product.name or "",
                        qty,
                        amount,
                        cost,
                    )
                )
        if rows:
            all_qty = sum(r["qty"] for r in rows if r["kind"] == "customer")
            all_sale = sum(r["total_sale"] for r in rows if r["kind"] == "customer")
            all_cost = sum(r["total_cost"] for r in rows if r["kind"] == "customer")
            rows.append(
                self._build_row("total", "", _("TOTAL"), all_qty, all_sale, all_cost)
            )
        return rows

    @staticmethod
    def _build_row(kind, code, name, qty, amount, cost):
        unit = kind == "item" and qty
        return {
            "kind": kind,
            "code": code,
            "name": name,
            "qty": qty,
            "price_unit": amount / qty if unit else 0.0,
            "cost_unit": cost / qty if unit else 0.0,
            "margin_unit": (amount - cost) / qty if unit else 0.0,
            "total_sale": amount,
            "total_cost": cost,
            "total_margin": amount - cost,
            "margin_percent": (amount - cost) / amount * 100.0 if amount else 0.0,
        }

    # ---- acciones ----------------------------------------------------------------------
    def action_show(self):
        """Calcula el listado y lo abre en modo lista."""
        self.ensure_one()
        self.line_ids.sudo().unlink()
        Line = self.env["todopintura.customer.item.report.line"].sudo()
        # En el listado el cliente es el grupo (su cabecera lleva los totales): solo
        # se guardan las filas de artículo, cada una con el cliente al que pertenece.
        customer = ""
        values = []
        for row in self._get_rows():
            if row["kind"] == "customer":
                customer = f"{row['name']} ({row['code']})" if row["code"] else row["name"]
            elif row["kind"] == "item":
                values.append(
                    dict(row, report_id=self.id, sequence=len(values) + 1, customer_label=customer)
                )
        Line.create(values)
        return {
            "type": "ir.actions.act_window",
            "name": _("Listado acumulado de artículos por cliente"),
            "res_model": "todopintura.customer.item.report.line",
            "view_mode": "list",
            "views": [
                (self.env.ref("todopintura_user_groups.view_customer_item_report_line_list").id, "list")
            ],
            "search_view_id": self.env.ref(
                "todopintura_user_groups.view_customer_item_report_line_search"
            ).id,
            "domain": [("report_id", "=", self.id)],
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
                "group_by": ["customer_label"],  # agrupado por clientes por defecto
            },
            "target": "current",
        }

    def action_export_xlsx(self):
        """Descarga el listado en Excel (sin las columnas de coste a quien no las ve)."""
        self.ensure_one()
        content = self._build_xlsx(self._get_rows())
        attachment = self.env["ir.attachment"].create(
            {
                "name": "listado_acumulado_articulos_por_cliente.xlsx",
                "datas": base64.b64encode(content),
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

    def _build_xlsx(self, rows):
        import xlsxwriter

        show_cost = self.env.user.has_group(COST_GROUP)
        stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(stream, {"in_memory": True})
        sheet = workbook.add_worksheet(_("Artículos por cliente")[:31])
        head = workbook.add_format({"bold": True, "bg_color": "#714B67", "font_color": "#FFFFFF", "border": 1})
        number = workbook.add_format({"num_format": "#,##0.00"})
        number_bold = workbook.add_format({"num_format": "#,##0.00", "bold": True, "bg_color": "#E9ECEF"})
        percent = workbook.add_format({"num_format": '0.00"%"'})
        percent_bold = workbook.add_format({"num_format": '0.00"%"', "bold": True, "bg_color": "#E9ECEF"})
        text = workbook.add_format({})
        text_bold = workbook.add_format({"bold": True, "bg_color": "#E9ECEF"})
        title = workbook.add_format({"bold": True, "font_size": 13})

        columns = [
            (_("Código"), "code", "text", 14),
            (_("Descripción"), "name", "text", 46),
            (_("Cantidad"), "qty", "number", 12),
            (_("Precio venta"), "price_unit", "number", 14),
        ]
        if show_cost:
            columns += [(_("Precio costo"), "cost_unit", "number", 14), (_("Margen"), "margin_unit", "number", 12)]
        columns.append((_("T. Venta"), "total_sale", "number", 14))
        if show_cost:
            columns += [
                (_("T. Costo"), "total_cost", "number", 14),
                (_("T. Margen"), "total_margin", "number", 14),
                (_("% Margen"), "margin_percent", "percent", 11),
            ]
        sheet.write(0, 0, _("Listado acumulado de artículos por cliente"), title)
        sheet.write(
            1, 0, _("Del %(from)s al %(to)s", **{"from": self.date_from, "to": self.date_to})
        )
        for col, (label, _key, _kind, width) in enumerate(columns):
            sheet.write(3, col, label, head)
            sheet.set_column(col, col, width)
        for index, row in enumerate(rows, start=4):
            bold = row["kind"] != "item"
            unit_columns = row["kind"] == "item"
            for col, (_label, key, kind, _width) in enumerate(columns):
                value = row[key]
                if kind == "text":
                    sheet.write_string(index, col, value or "", text_bold if bold else text)
                    continue
                if key in ("price_unit", "cost_unit", "margin_unit") and not unit_columns:
                    sheet.write_blank(index, col, None, number_bold if bold else number)
                    continue
                fmt = (
                    (percent_bold if bold else percent)
                    if kind == "percent"
                    else (number_bold if bold else number)
                )
                sheet.write_number(index, col, value or 0.0, fmt)
        sheet.freeze_panes(4, 2)
        workbook.close()
        return stream.getvalue()


class CustomerItemReportLine(models.TransientModel):
    _name = "todopintura.customer.item.report.line"
    _description = "Línea del listado acumulado de artículos por cliente"
    _order = "report_id, sequence"

    report_id = fields.Many2one(
        "todopintura.customer.item.report", ondelete="cascade", index=True
    )
    sequence = fields.Integer()
    kind = fields.Selection(
        [("customer", "Cliente"), ("item", "Artículo"), ("total", "Total")],
        string="Tipo",
    )
    customer_label = fields.Char(string="Cliente", index=True)
    code = fields.Char(string="Código")
    name = fields.Char(string="Descripción")
    qty = fields.Float(string="Cantidad", digits="Product Unit", aggregator="sum")
    # Valores por unidad: no se suman en la cabecera de un cliente.
    price_unit = fields.Float(string="Precio venta", digits="Product Price", aggregator=False)
    cost_unit = fields.Float(
        string="Precio costo", digits="Product Price", groups=COST_GROUP, aggregator=False
    )
    margin_unit = fields.Float(
        string="Margen", digits="Product Price", groups=COST_GROUP, aggregator=False
    )
    total_sale = fields.Float(string="T. Venta", digits="Product Price", aggregator="sum")
    total_cost = fields.Float(
        string="T. Costo", digits="Product Price", groups=COST_GROUP, aggregator="sum"
    )
    total_margin = fields.Float(
        string="T. Margen", digits="Product Price", groups=COST_GROUP, aggregator="sum"
    )
    margin_percent = fields.Float(
        string="% Margen", digits=(12, 2), groups=COST_GROUP, aggregator="sum"
    )

    @api.model
    def formatted_read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        """En la cabecera de cada cliente el % de margen es margen / venta del grupo
        (no la suma de los porcentajes de sus artículos)."""
        groups = super().formatted_read_group(
            domain, groupby, aggregates, having=having, offset=offset, limit=limit, order=order
        )
        percent_key = next((a for a in aggregates if a.startswith("margin_percent:")), None)
        if percent_key:
            for group in groups:
                sale = group.get("total_sale:sum")
                margin = group.get("total_margin:sum")
                if sale is not None and margin is not None:
                    group[percent_key] = margin / sale * 100.0 if sale else 0.0
        return groups
