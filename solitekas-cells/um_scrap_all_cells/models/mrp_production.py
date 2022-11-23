from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class UminaRepair(models.Model):
    _inherit = 'mrp.production'

    is_scrapped = fields.Boolean(string='Scrapped product', readonly=True)

    def button_scrap_multiple(self):
        # Not going to use this currently. TODO: Clear code
        pass
