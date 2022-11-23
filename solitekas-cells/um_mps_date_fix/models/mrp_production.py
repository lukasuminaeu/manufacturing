# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model_create_multi
    def create(self, vals):
        #Description for this fix is in manifest file of this module.
        if ('date_planned_start' in vals[0] and \
        'date_deadline' in vals[0]):
            vals[0]['date_planned_start'] = vals[0]['date_planned_start'] + timedelta(hours=1)
            vals[0]['date_deadline'] = vals[0]['date_deadline'] + timedelta(hours=1)
        res = super(MrpProduction, self).create(vals)
        return res
        
