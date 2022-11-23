# -*- coding: utf-8 -*-

from odoo import _, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_lot_info(self):
        self.ensure_one()
        result = []
        for move in self.move_lines:
            lot_names = [line.lot_id.name for line in move.move_line_ids if line.lot_id]
            val = "%s - %s" % (move.product_id.default_code, '/'.join(lot_names))
            result.append(val)

        return result