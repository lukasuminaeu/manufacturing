
import logging

from odoo import _, api, exceptions, fields, models, tools
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)


class Lost(models.TransientModel):
    _inherit = 'crm.lead.lost'

    lost_reason = fields.Text('Lost Details',required=True)


    def action_lost_reason_apply(self):
        lead_id = self._context.get('active_id')
        if lead_id and self.lost_reason:
            lead = self.env['crm.lead'].browse(lead_id)
            lead.write({'reason_detail':self.lost_reason})
        return super(Lost, self).action_lost_reason_apply()
            