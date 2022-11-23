# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class WizardCancelReason(models.TransientModel):
    _name = 'sale.order.cancel'
    _description = 'Wizard Get Cancel Reason'

    cancel_reason_id = fields.Many2one('sale.cancel.reason', 'Cancel Reason')

    def action_cancel_reason_apply(self):
        sale = self.env['sale.order'].browse(self.env.context.get('active_id'))
        sale.write({'cancel_reason': self.cancel_reason_id.id})
        return sale.action_cancel()