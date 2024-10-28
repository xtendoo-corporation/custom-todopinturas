from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HREmployee(models.Model):
    _inherit = "hr.employee"

    access_code = fields.Char(
        string="Access Code",
        groups="hr.group_hr_user",
        copy=False,
        help="Access code used for changing cashier in the Point of Sale application.",
        unique=True,  # Asegura que el código de acceso sea único
    )

    @api.constrains('access_code')
    def _check_unique_access_code(self):
        for record in self:
            if record.access_code:
                existing_records = self.search_count(
                    [('access_code', '=', record.access_code), ('id', '!=', record.id)])
                if existing_records > 0:
                    raise ValidationError(
                        "The Access Code must be unique. The code '%s' is already in use." % record.access_code)
