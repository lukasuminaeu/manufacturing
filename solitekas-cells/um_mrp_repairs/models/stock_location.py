from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class StockLocation(models.Model):
    _inherit = "stock.location"

    is_repair_location = fields.Boolean("Is Repair Location")


class StockQuantCustom(models.Model):
    _inherit = "stock.quant"

    is_available = fields.Boolean('Is available', compute='_get_availability', store=False)

    @api.depends('available_quantity')
    def _get_availability(self):
        for record in self:
            record.is_available = True if record.available_quantity > 0 else False