from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class BZ(models.Model):
    _inherit = 'product.product'

    buffer_zone_id = fields.Many2one('stock.location', 'Buffer Zone')
