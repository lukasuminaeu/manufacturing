# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, tools
import logging

_logger = logging.getLogger(__name__)


class InstallationTypeTags(models.Model):
    _name = "installation.type.tags"
    _description = "Installation type tags"

    name = fields.Char('Installation type tag name')
    color = fields.Integer('Color Index')
