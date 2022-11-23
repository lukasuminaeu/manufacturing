from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class UminaQualityCheckWizard(models.TransientModel):
    _inherit = 'quality.check.wizard'

    workorder_id = fields.Many2one('mrp.workorder','Workorder')
