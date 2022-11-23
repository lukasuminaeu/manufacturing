# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    produced_class = fields.Selection(related='lot_id.produced_class')
    lot_name = fields.Char(related='lot_id.name')
