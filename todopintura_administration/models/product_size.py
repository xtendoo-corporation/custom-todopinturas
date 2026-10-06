import re

from odoo import api, fields, models

_NUMBER_UNIT_RE = re.compile(r'^(\d[\d.,]*)\s*(.*)$')
_THOUSANDS_RE = re.compile(r'^\d{1,3}(\.\d{3})+$')
_GR_ML_RE = re.compile(r'^(gr|g)\s*/\s*ml$')
_KG_LT_RE = re.compile(r'^(?:(?:kg|k|kgs)\s*/\s*(?:lt|l)|(?:lt|l)\s*/\s*(?:kg|k))$')
_KG_RE = re.compile(r'^(kg|kgs|kilos?)$')
_LT_RE = re.compile(r'^(lt|l|litros?)$')
_ML_RE = re.compile(r'^ml$')


class ProductSize(models.Model):
    _name = 'product.size'
    _description = 'Tamaño de producto'
    _order = 'code, id'

    name = fields.Char('Tamaño', required=True)
    code = fields.Integer('Código', required=True, index=True, help='Código del tamaño en el sistema anterior.')
    weight = fields.Float(
        'Peso (kg)', digits='Stock Weight', compute='_compute_weight_volume', store=True, readonly=False,
        help='Se calcula del nombre ("5 Kg/Lt" = 5 kg; "50 Gr/Ml" = 0,05 kg). Se copia al producto al importar.')
    volume = fields.Float(
        'Volumen (m³)', digits='Volume', compute='_compute_weight_volume', store=True, readonly=False,
        help='Se calcula del nombre ("5 Kg/Lt" = 5 litros = 0,005 m³). Se copia al producto al importar.')

    _code_uniq = models.Constraint('unique(code)', 'Ya existe un tamaño con ese código.')

    @api.model
    def _parse_weight_volume(self, name):
        """Devuelve (peso en kg, volumen en m³) deducidos del nombre; 0 si no aplica.

        "N Kg/Lt" (y variantes K/L, LT/KG) -> N kg y N litros (se asume 1 L = 1 kg);
        "N Gr/Ml" -> N/1000 kg y N/1000 L; "N kg" solo peso; "N lt" solo volumen;
        "N ml" (entero >= 10) -> volumen. Metros, m2, "Rollo", etc. no tienen peso ni volumen.
        """
        match = _NUMBER_UNIT_RE.match(' '.join((name or '').lower().split()))
        if not match:
            return 0.0, 0.0
        number_text, unit = match.groups()
        number_text = number_text.rstrip('.,')
        if _THOUSANDS_RE.match(number_text):
            number_text = number_text.replace('.', '')
        try:
            number = float(number_text.replace(',', '.'))
        except ValueError:
            return 0.0, 0.0
        unit = unit.strip().rstrip('.').strip()

        weight_kg = liters = 0.0
        if _GR_ML_RE.match(unit):
            weight_kg = liters = number / 1000
        elif _KG_LT_RE.match(unit):
            weight_kg = liters = number
        elif _KG_RE.match(unit):
            weight_kg = number
        elif _LT_RE.match(unit):
            liters = number
        elif _ML_RE.match(unit) and number >= 10 and number.is_integer():
            liters = number / 1000
        return weight_kg, liters / 1000

    @api.depends('name')
    def _compute_weight_volume(self):
        for size in self:
            size.weight, size.volume = self._parse_weight_volume(size.name)
