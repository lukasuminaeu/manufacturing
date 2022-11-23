# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import psycopg2
import time

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    product_class_a = fields.Many2one("product.product", "Class A")
    product_class_b = fields.Many2one("product.product", "Class B")
    product_class_c = fields.Many2one("product.product", "Class C")

    # def test111(self):
    #     tst = self.env['mrp.production.schedule']
    #     print(tst)
    #     for i in tst:
    #         print('test123')
    #         print(i.get_mps_view_state())
    

    def write(self, vals):
        res = super(MrpBom, self).write(vals)
        if 'bom_line_ids' in vals:
            for bom in self:
                if bom.product_id:
                    product_ids = [bom.product_id.id]
                elif bom.product_tmpl_id:
                    product_ids = bom.product_tmpl_id.product_variant_ids.ids

                for product_id in product_ids:
                    schedule_ids = self.env['mrp.production.schedule'].search([('product_id', '=', product_id), ('is_final_product', '=', True)])
                    for schedule in schedule_ids:
                        schedule.recalculate_components()
                if product_ids:
                    self.env['bus.bus']._sendone('mrp_mps_channel', 'refresh_mps', {'product_ids': product_ids, 'method': 'create'})
        return res


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def test111(self):
        print('test1111111')
        component_ids = self.move_raw_ids.mapped('product_id')
        parent_id = self.main_production_id and self.main_production_id.product_id or self.product_id
        tst = self.env['mrp.production.schedule'].search([
            ('parent_id.product_id', '=', parent_id.id),
            ('product_id', 'in', component_ids.ids),
        ])
        for i in tst:
            i.get_production_schedule_view_state()

        # print(tst[0].get_mps_view_state())
        # get_production_schedule_view_state
        # print(tst[0].get_mps_view_state())
        # for i in tst:
        #     i.get_production_schedule_view_state()


    @api.model_create_multi
    def create(self, vals):
        # if ('date_planned_start' in vals[0] and \
        # 'date_deadline' in vals[0]):
        #     vals[0]['date_planned_start'] = vals[0]['date_planned_start'] + timedelta(hours=2)
        #     vals[0]['date_deadline'] = vals[0]['date_deadline'] + timedelta(hours=2)

        res = super(MrpProduction, self).create(vals)
        for r in res:
            r.recompute_other_mo()
        if not self.env.context.get('skip_bus'):
            self.env['bus.bus']._sendone('mrp_mps_channel', 'refresh_mps', {'product_ids': [r.product_id.id for r in res], 'method': 'create'})
        self.env['bus.bus']._sendone('mrp_production', 'calendar_update', {'method': 'create'})

        for pr in res:
            #Make different destination location for final products when created from MPS
            if pr.product_id.is_final_product:
                sandelis = self.env.ref('um_mrp_data.stock_location_sandelis')
                pr.location_dest_id = sandelis.id

        return res

    def write(self, vals):
        bus_obj = self.env['bus.bus']
        date_mo = {}
        for mo in self:
            date_mo[mo.id] = mo.date_planned_start
        res = super(MrpProduction, self).write(vals)
        if 'date_planned_start' in vals or 'date_planned_finished' in vals \
        and self.product_id.is_final_product:
            for mo in self:
                # Edvardas ADD: if planned date of the final production order
                # was changed, we want to change date of all child production
                # orders and all related pickings/stock_moves
                mo.change_date_planned()
                # Edvardas END
                old_date = date_mo[mo.id].date()
                new_date = mo.date_planned_start.date()
                if old_date.isocalendar()[1] != new_date.isocalendar()[1]:  # If the change is between weeks
                    start_old_date = old_date - timedelta(days=old_date.weekday())
                    end_old_date = start_old_date + timedelta(days=6)

                    old_forecast_id = self.env['mrp.product.forecast'].search(
                        [('production_schedule_id.product_id', '=', mo.product_id.id), ('date', '>=', start_old_date),
                         ('date', '<=', end_old_date)])
                         
                    for old_frc in old_forecast_id:
                        new_qty = old_frc.replenish_qty - mo.product_qty
                        # If the amount is positive we will deduct it
                        if new_qty >= 0:
                            old_frc.replenish_qty = new_qty
                        # If not we will remove the forecast
                        else:
                            old_frc.unlink()
            bus_obj._sendone('mrp_production', 'calendar_update', {'method': 'write'})
        if not self.env.context.get('skip_bus'):
            bus_obj._sendone('mrp_mps_channel', 'refresh_mps', {'product_ids': [mo.product_id.id for mo in self], 'method': 'write'})
        if not self.env.context.get('recomputed'):
            for mo in self:
                mo.recompute_other_mo()
        return res

    def unlink(self):
        self.env['bus.bus']._sendmany(
            [
                ['mrp_mps_channel', 'refresh_mps', {'product_ids': [], 'method': 'unlink'}],
                ['mrp_production', 'calendar_update', {'method': 'unlink'}]
            ])
        return super(MrpProduction, self.with_context(skip_bus=True)).unlink()

    def _get_mo_list_dates(self):
        self.ensure_one()
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        date_start = pytz.utc.localize(self.date_planned_start).astimezone(tz).replace(tzinfo=None).date()
        datetime_end = pytz.utc.localize(self.date_planned_finished).astimezone(tz).replace(tzinfo=None)
        # Try to fix when it finishes the same day but at 0 hours
        if datetime_end.hour == 0 and datetime_end.minute == 0 and datetime_end.second == 0:
            date_end = pytz.utc.localize(self.date_planned_finished).astimezone(tz).replace(tzinfo=None).date() - timedelta(days=1)
        else:
            date_end = pytz.utc.localize(self.date_planned_finished).astimezone(tz).replace(tzinfo=None).date()

        delta = date_end - date_start  # as timedelta

        days = []

        for i in range(delta.days + 1):
            day = date_start + timedelta(days=i)
            days.append(day)

        return days
    
    def adjust_end_date(self):
        if self.product_qty and self.date_planned_start:
            # if there's a remainder, add +1
            if (self.product_qty % 600) != 0:
                days = (self.product_qty // 600)+1
                self.write({'date_planned_finished': self.date_planned_start + timedelta(days=days) - timedelta(minutes=240)})
            # if not, divide by 600 using // to return an int not a float
            else:  
                days = self.product_qty // 600
                self.write({'date_planned_finished': self.date_planned_start + timedelta(days=days) - timedelta(minutes=240)})
        return days

    def _push_after_date(self, last_mo_date, next_call=False):
        if not self._is_source_MPS() and self.is_final_product:
            localized_date = self._get_mo_list_dates()[0]
            if localized_date != self.date_planned_start.date():
                next_date = last_mo_date + timedelta(days=2)
            else:
                next_date = last_mo_date + timedelta(days=1)

            new_start_date = self.date_planned_start.replace(year=next_date.year, month=next_date.month, day=next_date.day)

            self.with_context(recomputed=True).write({'date_planned_start': new_start_date})
            
            days=self.with_context(recomputed=True).adjust_end_date()
            self.change_date_planned()

            #self.with_context(recomputed=True)._onchange_date_planned_start()

            mo_dates = self._get_mo_list_dates()
            has_weekend = any([d for d in mo_dates if d.isoweekday() in (6, 7)])

            if has_weekend and not next_call and days < 6:
                # We will recompute only once, if not it might be due the timespan for the event is higher than 5 days
                last_sunday = mo_dates[0] + timedelta(days=7 - mo_dates[0].isoweekday())
                self._push_after_date(last_sunday, next_call=True)

    def _is_source_MPS(self):
        # Functions 'recompute_other_mo' and '_push_after_date' should be inactive if the source is MPS, because then records in MPS are moved
        # and working with MPS becomes impossible; because we use multi-level BoM, we need to check origin of all source MOs
        for production in self:
            if production.origin == 'MPS':
                # We change it to MPS Updated so this order would not be ignored the 2nd time we try to drag and drop it
                #production.write({'origin': 'MPS Updated'}) 
                return True # This greatly increases performance when working with MOs calendar because it will have domain to show only the Final Products

            production_ids = self.env['mrp.production']
            current_production_ids = self.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids
            production_ids += current_production_ids

            while production_ids:
                if production_ids[0].origin == 'MPS':
                    # We change it to MPS Updated so this order would not be ignored the 2nd time we try to drag and drop it
                    #production_ids[0].write({'origin': 'MPS Updated'}) 
                    return True
                production_ids -= production_ids[0]
            return False

    def recompute_other_mo(self): 
        if not self._is_source_MPS() and self.is_final_product:
            tz = pytz.timezone(self.env.user.tz or 'UTC')
            date_tz_start = pytz.utc.localize(self.date_planned_start).astimezone(tz).replace(tzinfo=None)
            date_start_1 = date_tz_start.replace(hour=0, minute=0, second=0)
            date_start_2 = date_tz_start.replace(hour=23, minute=59, second=59)

            # 1. Let's find the older MO with an overlap
            oldest_mo = self.search(
                [('date_planned_start', '<', date_start_1),
                ('date_planned_finished', '>=', date_start_2),
                ('state', 'not in', ['done', 'cancel', 'progress', 'to_close']),
                ('id', '!=', self.id)],
                order="date_planned_start ASC", limit=1)

            earliest_date = oldest_mo and oldest_mo.date_planned_start or date_tz_start
            earliest_date = earliest_date.replace(hour=0, minute=0, second=0)

            domain = [('date_planned_start', '>=', earliest_date), ('state', 'not in', ['done', 'cancel', 'progress', 'to_close'])]
            if not oldest_mo:
                # If there is no conflict with other MO that is older
                mo_dates = self._get_mo_list_dates()
                has_weekend = any([d for d in mo_dates if d.isoweekday() in (6, 7)])
                if has_weekend and len(mo_dates) > 1 and len(mo_dates) < 6:  # If the event that we are moving is longer than 1 day then it won't be able to put on weekends
                    last_sunday = mo_dates[0] + timedelta(days=7-mo_dates[0].isoweekday())
                    self._push_after_date(last_sunday)
                    # self.change_date_planned()
                mo_dates_used = self._get_mo_list_dates()
                domain.append(('id', '!=', self.id))
            else:
                mo_dates_used = []
            for index, mo in enumerate(self.search(domain, order="date_planned_start ASC")):
                mo_dates = mo._get_mo_list_dates()

                has_weekend = any([d for d in mo_dates if d.isoweekday() in (6, 7)])

                if has_weekend and len(mo_dates) > 1 and len(mo_dates) < 6:
                    last_sunday = mo_dates[0] + timedelta(days=7 - mo_dates[0].isoweekday())
                    mo._push_after_date(last_sunday)
                    mo_dates = mo._get_mo_list_dates()

                if any(x in mo_dates_used for x in mo_dates):
                    mo._push_after_date(mo_dates_used[-1])

                    mo_dates = mo._get_mo_list_dates()

                mo_dates_used += mo_dates


        
