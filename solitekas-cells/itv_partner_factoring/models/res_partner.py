# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = ['res.partner']

    is_factoring = fields.Boolean(string=u'Factoring Company', default=False)
    factoring_message = fields.Html(string=u'Factoring Message') 

    
    
    factoring_id = fields.Many2one(
        string=u'factoring_id',
        comodel_name='res.partner',
        ondelete='set null',
    )
    

    factoring_ids = fields.One2many(
        string=u'Factoring Companies',
        comodel_name='res.partner',
        inverse_name='factoring_id',
        domain=[('is_factoring','=',True)]
        
    )
    