from odoo import fields, models
from odoo.tools import frozendict


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    sequence = fields.Integer(
        string='Orden en el menú Imprimir',
        default=10,
        help="Los informes con menor valor salen antes en el menú Imprimir. "
        "Con el mismo valor se mantiene el orden por defecto de Odoo.",
    )


class IrActionsActions(models.Model):
    _inherit = 'ir.actions.actions'

    def _get_bindings(self, model_name):
        result = super()._get_bindings(model_name)
        reports = result.get('report')
        if not reports:
            return result
        # Odoo solo ordena por 'sequence' las acciones de tipo 'action'; los
        # informes salen por id. sorted() es estable: a igual 'sequence' se
        # conserva el orden original.
        result = dict(result)
        result['report'] = tuple(
            sorted(reports, key=lambda vals: vals.get('sequence', 10))
        )
        return frozendict(result)
