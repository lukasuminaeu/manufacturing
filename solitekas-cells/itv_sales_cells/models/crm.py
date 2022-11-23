# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class Team(models.Model):
    _inherit = 'crm.team'

    country_ids = fields.Many2many('res.country', 'crm_team_country_rel', 'team_id', 'country_id', string='Countries')

