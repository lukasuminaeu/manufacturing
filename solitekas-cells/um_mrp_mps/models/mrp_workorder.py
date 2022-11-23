# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def button_finish(self):
        end_date = datetime.now()
        for workorder in self:
            if workorder.state in ('done', 'cancel'):
                continue
            workorder.end_all()

            vals = {
                'qty_produced': workorder.qty_produced or workorder.qty_producing or workorder.qty_production,
                'state': 'done',
                'date_finished': end_date,
                # Umina edit: commented out below line, because after last intermediate product ([10])
                # and if the production was produced earlier than planned (for example one week before). 
                # Then MPS was showing wrong values. (There was some negative values appearing).
                # 'date_planned_finished': end_date,
                'costs_hour': workorder.workcenter_id.costs_hour
            }
            if not workorder.date_start:
                vals['date_start'] = end_date

            if not workorder.date_planned_start or end_date < workorder.date_planned_start:
                vals['date_planned_start'] = end_date
            workorder.write(vals)

            workorder._start_nextworkorder()
        return True
    
