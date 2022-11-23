# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    company_code = fields.Char('Company Code', help="Company Registry Code")

    
