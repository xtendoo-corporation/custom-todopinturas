from odoo import models, tools
from odoo.addons.web.controllers.utils import clean_action


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _tp_albaran_report(self, valued=None):
        """Informe de albarán Todo Pintura: valorado si el cliente tiene el albarán
        valorado marcado (o se fuerza con `valued=True`), estándar en otro caso."""
        if valued is None:
            valued = bool(self) and all(picking._tp_report_is_valued() for picking in self)
        xmlid = (
            'todopintura_administration.action_report_albaran_todopintura_valorado'
            if valued
            else 'todopintura_administration.action_report_albaran_todopintura'
        )
        return self.env.ref(xmlid, raise_if_not_found=False)

    def do_print_picking(self):
        """El botón Imprimir de un albarán pendiente también usa el albarán Todo Pintura."""
        report = self._tp_albaran_report()
        if not report:
            return super().do_print_picking()
        self.write({'printed': True})
        return report.report_action(self)

    def _get_autoprint_report_actions(self):
        """La impresión automática del albarán usa el albarán Todo Pintura."""
        actions = super()._get_autoprint_report_actions()
        pickings = self.filtered(lambda p: p.picking_type_id.auto_print_delivery_slip)
        report = pickings._tp_albaran_report()
        if not report or not pickings:
            return actions
        for index, action in enumerate(actions):
            if action.get('report_name') == 'stock.report_deliveryslip':
                new_action = report.report_action(pickings.ids, config=False)
                clean_action(new_action, self.env)
                actions[index] = new_action
        return actions

    def _tp_report_observations(self):
        """Observaciones escritas en el pedido de TPV (o en el pedido de venta creado
        desde el TPV) que originó este albarán, para imprimirlas bajo su número."""
        self.ensure_one()
        texts = []
        if 'pos_order_id' in self._fields:
            texts.append(self.pos_order_id.pos_observations if 'pos_observations' in self.pos_order_id._fields else False)
        if 'sale_id' in self._fields and 'pos_observations' in self.sale_id._fields:
            texts.append(self.sale_id.pos_observations)
        return '\n\n'.join(dict.fromkeys(t.strip() for t in texts if t and t.strip()))

    def _tp_report_copies(self):
        """Etiquetas de cada copia a imprimir: interna y para el cliente."""
        self.ensure_one()
        return ['COPIA INTERNA', 'COPIA PARA EL CLIENTE']

    def _tp_is_deposit_picking(self):
        """Albarán de un pedido enviado a depósito (destino: ubicación virtual Depósito)."""
        self.ensure_one()
        return bool(
            self.location_dest_id.usage == 'transit'
            and self.location_dest_id.name == 'Depósito'
        )

    def _tp_report_title(self):
        """DEPÓSITO para los albaranes de depósito; VTA CUENTA para clientes en modo
        depósito; ALBARAN en el resto."""
        self.ensure_one()
        if self._tp_is_deposit_picking():
            return 'DEPÓSITO Nº'
        partner = self.partner_id.commercial_partner_id
        if partner and 'pos_deposit_sale_enabled' in partner._fields \
                and partner.pos_deposit_sale_enabled:
            return 'VTA CUENTA Nº'
        return 'ALBARAN Nº'

    def _tp_report_date_str(self):
        self.ensure_one()
        date = self.date_done or self.scheduled_date
        if not date:
            return ''
        lang = self._get_report_lang()
        return tools.format_date(
            self.env, date, lang_code=lang, date_format="d 'DE' MMMM 'DE' y",
        ).upper()

    def _tp_report_is_valued(self):
        self.ensure_one()
        return bool(
            self.env.context.get('force_valued_picking')
            or self.partner_id.delivery_report_print_type == 'valued'
        )

    def _tp_report_salesperson(self):
        self.ensure_one()
        return self.sale_id.user_id or self.env['res.users']

    def _tp_report_tax_summary(self):
        """Base, IVA por tipo y recargo de equivalencia por tipo (albarán valorado)."""
        self.ensure_one()
        base = 0.0
        iva, recargo = {}, {}
        for move in self.move_ids.filtered(lambda m: m.product_uom_qty):
            line = move._get_conventional_report_source_line()
            if not line or line._name not in ('sale.order.line', 'pos.order.line'):
                continue
            qty = move._get_conventional_report_quantity()
            is_sale = line._name == 'sale.order.line'
            res = line.tax_ids.compute_all(
                move._get_conventional_report_discounted_price(),
                currency=line.order_id.currency_id,
                quantity=qty,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id if is_sale else line.order_id.partner_id,
            )
            base += res['total_excluded']
            for tax_vals in res['taxes']:
                tax = self.env['account.tax'].browse(tax_vals['id'])
                is_re = 'recargo' in (tax.tax_group_id.name or '').lower()
                bucket = recargo if is_re else iva
                entry = bucket.setdefault(tax.amount, 0.0)
                bucket[tax.amount] = entry + tax_vals['amount']
        total = base + sum(iva.values()) + sum(recargo.values())
        return {
            'base': base,
            'iva': sorted(iva.items()),
            'recargo': sorted(recargo.items()),
            'total': total,
        }
