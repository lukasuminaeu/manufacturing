
from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    domain = ['|',
              ('category_id', '=', "Platforma"),
              ('category_id', '=', "Platforma2")
              ]
    extension_platform_id = fields.Many2one("res.partner", domain=domain)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['extension_platform_id'] = ", s. extension_platform_id as extension_platform_id"
        groupby += ', s.extension_platform_id '
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)