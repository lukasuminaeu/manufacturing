
import logging

from odoo import _, api, exceptions, fields, models, tools
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)


class category(models.Model):
    _name = 'crm.lead.product.category'
    _description = u'Product Category'

    name = fields.Char(
        string=u'Name',
        required=True
    )


    
    
