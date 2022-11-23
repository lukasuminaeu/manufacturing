# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, tools
import logging

_logger = logging.getLogger(__name__)


class SupplierTags(models.Model):
    _name = "supplier.tags"
    _description = "Supplier tags"

    name = fields.Char('Supplier tag name')
    color = fields.Integer('Color Index')
