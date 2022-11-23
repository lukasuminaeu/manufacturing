# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    
    _inherit = ['sale.order']



    factoring_id = fields.Many2one(
        string=u'Factoring',
        comodel_name='res.partner',
        ondelete='set null',
        domain=[('is_factoring','=',True)]
    )
    
    is_factoringable = fields.Boolean(
        string=u'Factoring Available',
        compute='_compute_factoring_available', default=False, store=True )
    
    @api.depends('partner_id')
    def _compute_factoring_available(self):
        for record in self:
            record.is_factoringable =False
            if record.partner_id:
                if len(record.partner_id.factoring_ids) > 0:
                    record.is_factoringable =True
                  
        return True
    
    
    
