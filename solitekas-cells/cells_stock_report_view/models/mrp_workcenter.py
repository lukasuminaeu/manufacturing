# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, _


class WorkCenter(models.Model):
    _inherit = 'mrp.workcenter'

    def _domain_location_id(self):
        return [('usage', 'in', ['internal'])]

    location_id = fields.Many2one('stock.location', 'Location', domain=lambda self: self._domain_location_id())
