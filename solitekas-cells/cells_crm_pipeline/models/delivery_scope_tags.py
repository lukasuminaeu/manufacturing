# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, tools
import logging

_logger = logging.getLogger(__name__)


class DeliveryScopeTags(models.Model):
    _name = "delivery.scope.tags"
    _description = "Delivery scope tags"

    name = fields.Char('Delivery scope tag name')
    color = fields.Integer('Color Index')
