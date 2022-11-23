# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    _sql_constraints = [
        ('product_lot_name', 'UNIQUE (product_id, name, produced_class, company_id)', 'Lot name for product must be unique.')
    ]