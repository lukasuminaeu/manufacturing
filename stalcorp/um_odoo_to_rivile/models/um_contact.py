# -*- coding: utf-8 -*-


from audioop import add
from venv import create
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import xml.etree.ElementTree as ET
import json
from requests.auth import HTTPBasicAuth
import requests
# current date and time
now = datetime.now() 


class Contacts(models.Model):
    _inherit = 'res.partner'

    # @api.model 
    # def create(self, vals): 
    #     if not self.unique_code:
    #         vals['unique_code'] = self.env['ir.sequence'].next_by_code('unique.client_code')      

    #     return super(Contacts, self).create(vals)

    # Override this function to get extra field (street2) and change fields position in computed contact_address_complete field
    @api.depends('street', 'street2', 'zip', 'city', 'country_id')
    def _compute_complete_address(self):
        for record in self:
            record.contact_address_complete = ''
            if record.street:
                record.contact_address_complete += record.street + ','
            else:
                record.contact_address_complete += ','
            if record.street2:
                record.contact_address_complete += record.street2 + ','
            else:
                record.contact_address_complete += ','
            if record.city:
                record.contact_address_complete += record.city + ','
            else:
                record.contact_address_complete += ','
            if record.state_id:
                record.contact_address_complete += record.state_id.name + ','
            else:
                record.contact_address_complete += ','
            if record.zip:
                record.contact_address_complete += record.zip + ','
            else:
                record.contact_address_complete += ','
            if record.country_id:
                record.contact_address_complete += record.country_id.name
            else:
                record.contact_address_complete += ','
            record.contact_address_complete = record.contact_address_complete.strip().strip(',')
