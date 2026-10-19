from odoo import api, fields, models, tools


class TodopinturaSalesReport(models.Model):
    _name = "todopintura.sales.report"
    _description = "Informe de ventas y rentabilidad Todo Pintura"
    _auto = False
    _order = "date desc, document_name desc, id"

    doc_type = fields.Selection(
        selection=[
            ("pos", "Pedido TPV"),
            ("sale", "Pedido de venta"),
            ("invoice_a4", "Factura A4"),
            ("invoice_simplified", "Factura simplificada"),
        ],
        string="Tipo de documento",
        readonly=True,
    )
    date = fields.Date(string="Fecha", readonly=True)
    document_name = fields.Char(string="Referencia", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    user_id = fields.Many2one("res.users", string="Comercial / Cajero", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén / Tienda", readonly=True)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    categ_id = fields.Many2one("product.category", string="Categoría", readonly=True)
    delivery_status = fields.Selection(
        selection=[
            ("delivered", "Entregado"),
            ("pending", "Pendiente de entrega"),
            ("na", "No aplica"),
        ],
        string="Entrega",
        readonly=True,
    )
    qty = fields.Float(string="Cantidad", readonly=True)
    amount = fields.Float(string="Venta (sin impuestos)", readonly=True)
    cost = fields.Float(string="Coste", readonly=True)
    margin = fields.Float(string="Margen", readonly=True)
    margin_percent = fields.Float(
        string="Margen (%)", compute="_compute_margin_percent", digits=(12, 2),
    )

    @api.depends("amount", "margin")
    def _compute_margin_percent(self):
        for line in self:
            line.margin_percent = line.margin / line.amount * 100.0 if line.amount else 0.0

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT row_number() OVER () AS id, t.*, t.amount - t.cost AS margin
                FROM (%s) t
            )
            """
            % (self._table, self._query())
        )

    @staticmethod
    def _std_cost(product_alias, company_expr):
        """Coste estándar del producto (propiedad por compañía, jsonb)."""
        return (
            "COALESCE((%s.standard_price ->> (%s)::text)::numeric, 0)"
            % (product_alias, company_expr)
        )

    def _query(self):
        pos_cost = self._std_cost("pp", "o.company_id")
        inv_cost = self._std_cost("pp", "m.company_id")
        sale_cost = self._std_cost("pp", "so.company_id")
        return f"""
            -- Pedidos del TPV pagados o contabilizados (los vinculados a un
            -- pedido de venta se cuentan en el pedido de venta)
            SELECT 'pos' AS doc_type,
                   o.date_order::date AS date,
                   o.name AS document_name,
                   o.partner_id AS partner_id,
                   o.user_id AS user_id,
                   spt.warehouse_id AS warehouse_id,
                   o.company_id AS company_id,
                   l.product_id AS product_id,
                   pt.categ_id AS categ_id,
                   CASE WHEN o.state IN ('done', 'invoiced')
                        THEN 'delivered' ELSE 'pending' END AS delivery_status,
                   l.qty AS qty,
                   l.price_subtotal AS amount,
                   l.qty * {pos_cost} AS cost
              FROM pos_order_line l
              JOIN pos_order o ON o.id = l.order_id
              JOIN pos_session s ON s.id = o.session_id
              JOIN pos_config c ON c.id = s.config_id
              LEFT JOIN stock_picking_type spt ON spt.id = c.picking_type_id
              JOIN product_product pp ON pp.id = l.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE o.state IN ('paid', 'done', 'invoiced')

            UNION ALL

            -- Pedidos de venta confirmados
            SELECT 'sale' AS doc_type,
                   so.date_order::date AS date,
                   so.name AS document_name,
                   so.partner_id AS partner_id,
                   so.user_id AS user_id,
                   so.warehouse_id AS warehouse_id,
                   so.company_id AS company_id,
                   sol.product_id AS product_id,
                   pt.categ_id AS categ_id,
                   CASE WHEN so.delivery_status = 'full'
                        THEN 'delivered' ELSE 'pending' END AS delivery_status,
                   sol.product_uom_qty AS qty,
                   sol.price_subtotal AS amount,
                   sol.product_uom_qty * {sale_cost} AS cost
              FROM sale_order_line sol
              JOIN sale_order so ON so.id = sol.order_id
              JOIN product_product pp ON pp.id = sol.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE so.state = 'sale'
               AND sol.display_type IS NULL

            UNION ALL

            -- Facturas de cliente publicadas que NO vienen de un pedido TPV ni de un
            -- pedido de venta (las que sí, ya cuentan en su pedido): evita duplicar
            SELECT CASE WHEN j.code = 'SIMP' THEN 'invoice_simplified'
                        ELSE 'invoice_a4' END AS doc_type,
                   m.invoice_date AS date,
                   m.name AS document_name,
                   m.partner_id AS partner_id,
                   m.invoice_user_id AS user_id,
                   NULL::integer AS warehouse_id,
                   m.company_id AS company_id,
                   aml.product_id AS product_id,
                   pt.categ_id AS categ_id,
                   'na' AS delivery_status,
                   CASE WHEN m.move_type = 'out_refund' THEN -aml.quantity
                        ELSE aml.quantity END AS qty,
                   -aml.balance AS amount,
                   CASE WHEN m.move_type = 'out_refund' THEN -aml.quantity
                        ELSE aml.quantity END * {inv_cost} AS cost
              FROM account_move_line aml
              JOIN account_move m ON m.id = aml.move_id
              JOIN account_journal j ON j.id = m.journal_id
              JOIN product_product pp ON pp.id = aml.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE m.move_type IN ('out_invoice', 'out_refund')
               AND m.state = 'posted'
               AND aml.display_type = 'product'
               AND NOT EXISTS (
                    SELECT 1 FROM pos_order po WHERE po.account_move = m.id)
               AND NOT EXISTS (
                    SELECT 1
                      FROM sale_order_line_invoice_rel rel
                      JOIN account_move_line l2 ON l2.id = rel.invoice_line_id
                     WHERE l2.move_id = m.id)
        """
