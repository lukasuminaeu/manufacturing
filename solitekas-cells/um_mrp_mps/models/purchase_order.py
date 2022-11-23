# -*- coding: utf-8 -*-
import logging

from datetime import timedelta
from odoo import api, fields, models, _
from odoo.tools.misc import format_date
_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model_create_multi
    def create(self, vals):
        line = super(PurchaseOrderLine, self).create(vals)
        if not self.env.context.get('skip_bus'):
            self.env['bus.bus']._sendone('mrp_mps_channel', 'refresh_mps', {'product_ids': [l.product_id.id for l in line]})
        return line

    def write(self, vals):
        res = super(PurchaseOrderLine, self).write(vals)
        if not self.env.context.get('skip_bus'):
            self.env['bus.bus']._sendone('mrp_mps_channel', 'refresh_mps', {'product_ids': [l.product_id.id for l in self]})
        return res


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _date_range_to_str(self):
        date_range = self._get_date_range()
        dates_as_str = []
        lang = self.env.context.get('lang')
        for date_start, date_stop in date_range:
            if self.manufacturing_period == 'month':
                dates_as_str.append(format_date(self.env, date_start, date_format='MMM yyyy'))
            elif self.manufacturing_period == 'week':
                
                week_1 = format_date(self.env, date_start, date_format='w')
                week_2 = format_date(self.env, date_stop - timedelta(days=1), date_format='w')

                #Added some additional logic below, because it was showing week number one week
                #forward for some reason. (for example - if current week is 29, at mps it was showing 30)
                week_1 = str(int(week_1) - 1)
                week_2 = str(int(week_2) - 1)

                if week_1 == week_2:
                    dates_as_str.append(_('Week %s', week_1))
                else:
                    dates_as_str.append(_('Week %s/%s' % (week_1, week_2)))
            else:
                dates_as_str.append(format_date(self.env, date_start, date_format='MMM d'))
        return dates_as_str