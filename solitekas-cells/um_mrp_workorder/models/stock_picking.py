# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools.safe_eval import safe_eval

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def compute_available_qty_set_workorder(self):
        for record in self:
            mo = record.env['mrp.production'].search([
                ('procurement_group_id', '=', record.group_id.id),
                ('state', 'not in', ('to_close', 'done', 'cancel'))
            ])
            
            if mo and mo.product_id.tracking not in ('serial'):
                mo.action_assign()

    def button_validate(self):
        res = super().button_validate()
        if res == True:
            self.compute_available_qty_set_workorder()
        return res