# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command, api, fields, models


class StockConsult(models.TransientModel):
    """Consulta de existencias de un producto, desglosada por almacén."""

    _name = "todopintura.stock.consult"
    _description = "Consulta de existencias por producto"

    product_id = fields.Many2one(
        "product.product", string="Producto", domain=[("is_storable", "=", True)]
    )
    period = fields.Selection(
        [("year", "Año en curso"), ("all", "Completo")],
        string="Periodo",
        default="year",
        required=True,
        help="Periodo de las columnas Entradas, Compras y Ventas. «Ex. ant.» es el "
        "stock a 1 de enero (solo en el año en curso).",
    )
    uom_id = fields.Many2one("uom.uom", related="product_id.uom_id", string="Unidad")
    line_ids = fields.One2many(
        "todopintura.stock.consult.line", "consult_id", compute="_compute_lines"
    )

    @api.depends("product_id", "period")
    def _compute_lines(self):
        for wizard in self:
            commands = [Command.clear()]
            if wizard.product_id:
                commands += [Command.create(v) for v in wizard._get_line_values()]
            wizard.line_ids = commands

    def _get_line_values(self):
        """Una línea por almacén. Se calcula con sudo: el usuario ve todos los almacenes."""
        self.ensure_one()
        product = self.product_id.sudo()
        year_start = fields.Datetime.to_datetime(fields.Date.today().replace(month=1, day=1))
        Move = self.env["stock.move"].sudo()
        values = []
        for warehouse in self.env["stock.warehouse"].sudo().search(
            [("company_id", "in", self.env.companies.ids)], order="sequence, id"
        ):
            wh_id = warehouse.id
            in_wh = [("location_dest_id.warehouse_id", "=", wh_id)]
            out_wh = [("location_id.warehouse_id", "=", wh_id)]
            outside_src = [
                "|",
                ("location_id.warehouse_id", "=", False),
                ("location_id.warehouse_id", "!=", wh_id),
            ]
            base = [("product_id", "=", product.id), ("state", "=", "done")]
            if self.period == "year":
                base.append(("date", ">=", year_start))

            def qty(domain, base=base):
                return sum(Move.search(base + domain).mapped("quantity"))

            # Entradas: todo lo que llega de fuera del almacén (proveedores y traspasos).
            received = qty(
                in_wh + outside_src + [("location_id.usage", "in", ("supplier", "internal", "transit"))]
            )
            # Compras: lo recibido de pedidos de compra.
            purchased = qty(in_wh + [("purchase_line_id", "!=", False)])
            # Ventas: salidas a clientes menos devoluciones.
            sold = qty(out_wh + [("location_dest_id.usage", "=", "customer")]) - qty(
                in_wh + [("location_id.usage", "=", "customer")]
            )
            # A cuenta: unidades en pedidos de TPV en depósito (pendientes de liquidar).
            credit = sum(
                self.env["pos.order.line"]
                .sudo()
                .search(
                    [
                        ("product_id", "=", product.id),
                        ("order_id.state", "=", "deposit"),
                        ("order_id.config_id.picking_type_id.warehouse_id", "=", wh_id),
                    ]
                )
                .mapped("qty")
            )
            minimum = sum(
                self.env["stock.warehouse.orderpoint"]
                .sudo()
                .search([("product_id", "=", product.id), ("warehouse_id", "=", wh_id)])
                .mapped("product_min_qty")
            )
            product_wh = product.with_context(warehouse_id=wh_id)
            previous = (
                product_wh.with_context(to_date=year_start).qty_available
                if self.period == "year"
                else 0.0
            )
            values.append(
                {
                    "warehouse_id": wh_id,
                    "min_qty": minimum,
                    "prev_qty": previous,
                    "in_qty": received,
                    "purchase_qty": purchased,
                    "credit_qty": credit,
                    "sold_qty": sold,
                    "stock_qty": product_wh.qty_available,
                }
            )
        return values


class StockConsultLine(models.TransientModel):
    _name = "todopintura.stock.consult.line"
    _description = "Línea de consulta de existencias"

    consult_id = fields.Many2one("todopintura.stock.consult", ondelete="cascade")
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén")
    min_qty = fields.Float(string="Mínimo")
    prev_qty = fields.Float(string="Ex. ant.")
    in_qty = fields.Float(string="Entradas")
    purchase_qty = fields.Float(string="Compras")
    credit_qty = fields.Float(string="A cuenta")
    sold_qty = fields.Float(string="Ventas")
    stock_qty = fields.Float(string="Existencias")
