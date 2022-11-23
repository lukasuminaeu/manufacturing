from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"
    company_code = fields.Char(string="Company Code")
