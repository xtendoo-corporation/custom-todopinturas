# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class TodopinturaCommissionRate(models.Model):
    """Commission percentage per salesperson and/or product category.

    The calculation rule is pending a decision of the customer, so no rate is
    shipped: without records the commission report shows no commission.
    """

    _name = "todopintura.commission.rate"
    _description = "Porcentaje de comisión"
    _order = "user_id, categ_id, id"

    user_id = fields.Many2one(
        "res.users",
        string="Comercial",
        domain=[("share", "=", False)],
        index=True,
        help="Vacío = aplica a todos los comerciales.",
    )
    categ_id = fields.Many2one(
        "product.category",
        string="Categoría de producto",
        index=True,
        help="Vacío = aplica a todas las categorías.",
    )
    rate = fields.Float(string="Comisión (%)", required=True, digits=(5, 2))
    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta")
    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)

    @api.constrains("user_id", "categ_id", "rate")
    def _check_scope(self):
        for rate in self:
            if not rate.user_id and not rate.categ_id:
                raise ValidationError(
                    self.env._("Indique un comercial, una categoría o ambos.")
                )

    @api.constrains("rate")
    def _check_rate_range(self):
        for rate in self:
            if not 0 <= rate.rate <= 100:
                raise ValidationError(
                    self.env._("La comisión debe estar entre 0 y 100 %.")
                )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rate in self:
            if rate.date_from and rate.date_to and rate.date_from > rate.date_to:
                raise ValidationError(
                    self.env._("La fecha de inicio no puede ser posterior al fin.")
                )


class TodopinturaCommissionReport(models.Model):
    _name = "todopintura.commission.report"
    _description = "Ventas para comisiones"
    _auto = False
    _order = "date desc, id desc"

    date = fields.Date(readonly=True)
    user_id = fields.Many2one("res.users", string="Comercial", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    order_id = fields.Many2one("sale.order", string="Pedido", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    categ_id = fields.Many2one("product.category", string="Categoría", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    price_subtotal = fields.Monetary(string="Venta sin impuestos", readonly=True)
    rate = fields.Float(
        string="Comisión (%)", readonly=True, aggregator="avg", digits=(5, 2)
    )
    commission = fields.Monetary(string="Comisión", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL(
                "CREATE OR REPLACE VIEW %s AS (%s)",
                SQL.identifier(self._table),
                self._query(),
            )
        )

    def _query(self):
        # Rate priority: salesperson + category, salesperson only, category only.
        return SQL(
            """
            SELECT sol.id AS id,
                   so.date_order::date AS date,
                   so.user_id AS user_id,
                   so.partner_id AS partner_id,
                   so.id AS order_id,
                   sol.product_id AS product_id,
                   pt.categ_id AS categ_id,
                   so.company_id AS company_id,
                   so.currency_id AS currency_id,
                   sol.price_subtotal AS price_subtotal,
                   rate.rate AS rate,
                   COALESCE(sol.price_subtotal * rate.rate / 100.0, 0) AS commission
              FROM sale_order_line sol
              JOIN sale_order so ON so.id = sol.order_id
              JOIN product_product pp ON pp.id = sol.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
              LEFT JOIN LATERAL (
                    SELECT r.rate
                      FROM todopintura_commission_rate r
                     WHERE r.active
                       AND (r.user_id = so.user_id OR r.user_id IS NULL)
                       AND (r.categ_id = pt.categ_id OR r.categ_id IS NULL)
                       AND (r.date_from IS NULL OR r.date_from <= so.date_order::date)
                       AND (r.date_to IS NULL OR r.date_to >= so.date_order::date)
                       AND (r.company_id IS NULL OR r.company_id = so.company_id)
                  ORDER BY (r.user_id IS NOT NULL) DESC,
                           (r.categ_id IS NOT NULL) DESC,
                           r.id DESC
                     LIMIT 1
              ) rate ON TRUE
             WHERE so.state IN ('sale', 'done')
               AND sol.display_type IS NULL
            """
        )
