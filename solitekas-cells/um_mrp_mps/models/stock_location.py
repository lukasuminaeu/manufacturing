
import math
from datetime import datetime, timedelta
from odoo import models, fields, _, api


class StockLocation(models.Model):
    _inherit = "stock.location"

    is_stc_vbz = fields.Boolean("Is STC VBZ")

class StockMove(models.Model):
    _inherit = "stock.move"

    def refresh_mps(self):
        """Method used to refresh MPS after confirming move of purchase,
            because there was some problems with negative values when confirming so it needed
            a refresh
        """
        mps_obj = self.env['mrp.production.schedule'].search([
            ('product_id', '=', self.product_id.id),
        ])
        for i in mps_obj:
            i.get_production_schedule_view_state()

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for mv in self:
            if mv.state == 'done' and mv.picking_id.purchase_id.origin == 'MPS':
                mv.refresh_mps()

        return res

    def write(self, vals):
        if self and 'date' in vals:
            for move in self:
                old_date = move.date.date()
                res = super(StockMove, move).write(vals)  # scheduled_date
                new_date = move.date.date()
                if new_date:
                    # If the week is different from date then we will clean the previous week and recompute new week's suggested replenishment
                    if old_date.isocalendar()[1] != new_date.isocalendar()[1]:
                        start_old_date = old_date - timedelta(days=old_date.weekday())
                        end_old_date = start_old_date + timedelta(days=6)
                        start_new_date = new_date - timedelta(days=old_date.weekday())
                        end_new_date = start_new_date + timedelta(days=6)
                        old_forecast_id = self.env['mrp.product.forecast'].search([('production_schedule_id.product_id', '=', move.product_id.id), ('date', '>=', start_old_date), ('date', '<=', end_old_date)])
                        new_forecast_id = self.env['mrp.product.forecast'].search([('production_schedule_id.product_id', '=', move.product_id.id), ('date', '>=', start_new_date), ('date', '<=', end_new_date)])
                        if old_forecast_id:
                            # If forecast already exists then merge and unlink
                            if new_forecast_id:
                                for new_forecast in new_forecast_id:
                                    new_forecast['replenish_qty'] += move.product_qty
                                old_forecast_id.unlink()
                            # If doesn't exit, then move forecast to new date
                            else:
                                old_forecast_id['date'] = start_new_date
        else:
            res = super(StockMove, self).write(vals)  # scheduled_date
        return res
    
