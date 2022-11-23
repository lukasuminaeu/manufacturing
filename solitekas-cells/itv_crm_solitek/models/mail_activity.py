# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import _, api, exceptions, fields, models, tools
from datetime import datetime, timedelta, date

import logging

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = 'mail.activity'
    
    is_system = fields.Boolean('Created by system', default=False, help='Created by itv_crm_solitek')
