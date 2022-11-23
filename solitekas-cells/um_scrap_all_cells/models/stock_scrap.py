# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    def action_validate(self):
        """If scrapped product is intermediate product, then discount latter parent production."""
        res = super().action_validate()

        if not 'scrap_all' in self._context:
            for record in self:
                scrap_intermediate_product = record.production_id.bom_id.bom_line_ids.filtered(lambda x: x.product_id == record.product_id)
                if scrap_intermediate_product:
                    self.production_id.discount_source_qty(discount_self=True)

        return res

