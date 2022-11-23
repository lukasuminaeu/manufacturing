# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class QualityPoint(models.Model):
    _inherit = 'quality.point'

    determines_class = fields.Boolean("Determines Class")
    print_automatically = fields.Boolean("Print Automatically")


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    produced_class = fields.Selection([('A', 'A'), ('B', 'B'), ('C', 'C')], string='Class')
