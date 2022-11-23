# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'res.bank'

    bank_code_nr = fields.Char(string='Bank code')

class SaleOrder(models.Model):
    _inherit = 'res.partner.bank'
    
    bank_code_nr = fields.Char(related='bank_id.bank_code_nr', readonly=False)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    commitment_date = fields.Datetime('Delivery Date',
                                      states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                      copy=False, readonly=False, tracking=6,
                                      help="This is the delivery date promised to the customer. "
                                           "If set, the delivery order will be scheduled based on "
                                           "this date rather than product lead times.")
    cancel_reason = fields.Many2one('crm.lost.reason', string='Cancel Reason', index=True, track_visibility='onchange')

    # def action_cancel(self):
    #     return self.write({'state': 'cancel'})

    @api.model
    def on_sent_move_leads(self, record):
        _logger.debug('\n\n %s \n\n', record)
        crm_lead = self.env['crm.lead'].search([('id', '=', record.opportunity_id.id)])
        crm_stage = self.env['crm.stage'].search([('name', '=', 'Quotation')])
        crm_lead.write({'stage_id': crm_stage.id})

class CancelReason(models.Model):
    _name = 'sale.cancel.reason'
    _description = 'Get Sale Cancel Reason'

    name = fields.Char('Description', required=True, translate=True)
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [('name_uniq', 'unique (name)', "Cancel Reason already exists !")]
