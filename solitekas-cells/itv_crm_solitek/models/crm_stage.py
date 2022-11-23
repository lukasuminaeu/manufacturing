import logging

from odoo import _, api, exceptions, fields, models, tools
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)
#_logger.debug('\n%s',x)

class Stage(models.Model):
    _inherit = 'crm.stage'

    stage_selection2 = fields.Selection([('opportunity', 'Opportunity'), ('lead', 'Lead'), ], 'Type', default='opportunity')
    privacy_visibility = fields.Selection([('opportunity', 'Only opportunities can see it '),('lead', 'Restricted for leads'),],string='Visibility', required=True,default='opportunity',)
    after_how_many_days = fields.Integer('Days to complete task', default=0)
    activity_type = fields.Selection([('1', 'Email'), ('2', 'Call'), ('3', 'Meeting'), ('4', 'To Do'), ], 'Type of reminder', default='4')
    solitekas_description = fields.Text('Description', default='...')
    fields_required = fields.Many2many(string=u'Fields Required',comodel_name='ir.model.fields',relation='crm_stage_ir_model_fields_rel',
        domain=[('model','=','crm.lead')]
        )
    stage_salesperson = fields.Many2one(string=u'Stage Salesperson',comodel_name='res.users',ondelete='set null',)
    

