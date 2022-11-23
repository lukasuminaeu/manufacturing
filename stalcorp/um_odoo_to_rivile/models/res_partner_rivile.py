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
import re


class ContactsRivile(models.Model):
    _inherit = 'res.partner'

    unique_code = fields.Char(string='Kliento kodas Rivile',copy=False, index=True)


    def write(self, vals):
        res = super(ContactsRivile, self).write(vals)
        if 'test' not in self._context:
            self.contacts_odoo_to_rivile()
        return res

    # def write(self, vals):
    #     res = super(ContactsRivile, self).write(vals)
    #     print(self)
    #     if 'test' not in self._context:
    #         self.contacts_rivile_to_odoo
    #     return res

    @api.model
    def create(self, vals): 
        res = super(ContactsRivile, self).create(vals)
        if 'test1' not in self._context:
            res.contacts_odoo_to_rivile()
        return res


        

    def contacts_odoo_to_rivile(self):
        for rec in self:
            client_code = rec.unique_code
            # Contact name
            name = rec.name
            # Contact address
            address = rec.contact_address_complete 
            # Contact email
            email = rec.email
            # Contact phone
            phone = rec.phone
            # Contact mbile phone
            mobile_phone = rec.mobile
            # Contact tax id
            tax_id = rec.vat

            reqUrl = "https://api.manorivile.lt/client/v2"

            headersList = {
            "Accept": "*/*",
            "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
            "Content-Type": "application/json" 
            }

            payload = json.dumps({
                "method": "GET_N08_LIST",
                "params": {
                    "list": "A",
                    "fil": "n08_kodas_ks='{}'".format(client_code)
                }
            })

            response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            if not response.status_code == 200:
                raise UserError(response.text)

            
            if "N08" in response.text:
                payload = json.dumps({
                    "method": "EDIT_N08",
                    "params": {
                        "oper": "U"
                    },
                    "data": {
                        "N08": {
                            "N08_KODAS_KS": client_code,
                            "N08_PAV": name,
                            "N08_RUSIS": 1,
                            "N08_ADR": address,
                            "N08_E_MAIL": email,
                            "N08_TEL": phone,
                            "N08_MOB_TEL": mobile_phone,
                            "N08_PVM_KODAS": tax_id

                        }
                    }
                })
                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)
            else:
                payload = json.dumps({
                    "method": "EDIT_N08",
                    "params": {
                        "oper": "I"
                    },
                    "data": {
                        "N08": {
                            "N08_KODAS_KS": client_code,
                            "N08_PAV": name,
                            "N08_RUSIS": "1",
                            "N08_PVM_KODAS": tax_id,
                            "N08_KODAS_XS_P": "PVM",
                            "N08_KODAS_XS_T": "PVM",
                            "N08_KODAS_DS": "PT001",
                            "N08_ADR": address,
                            "N08_E_MAIL": email,
                            "N08_TEL": phone,
                            "N08_MOB_TEL": mobile_phone,
                            "N08_PVM_KODAS": tax_id
                        }
                    }
                })
                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)

    def contacts_rivile_to_odoo(self):
        aList = []
        
        # Contact code/ID
        # client_code = self.unique_code
        # if client_code:
        # Get next unique client code, this code will be using if there is no such Contact in Odoo
        # but there is i Rivile
        # next_unique_client_code = self.env['ir.sequence'].next_by_code('unique.client_code')

        reqUrl = "https://api.manorivile.lt/client/v2"

        headersList = {
        "Accept": "application/json",
        "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
        "Content-Type": "application/json" 
        }

        payload = json.dumps({
            "method": "GET_N08_LIST",
            "params": {
                "list": "A"
                # "fil": "n08_kodas_ks='{}'".format(client_code)
                # "fil": "n08_kodas_ks='11'"
            }
        })

        response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
        if not response.status_code == 200:
            raise UserError(response.text)

        # Get API Reuquest response
        aList = json.loads(response.text)
        # Init odoo contact codes list
        odoo_contact_codes = []
        # Get all available odoo contacts unique codes
        for contact in self.env['res.partner'].search([]):
            odoo_contact_codes.append(str(contact.unique_code))
        
        # Init odoo contact codes list
        rivile_contacts_codes = []
        if aList:
            # Get all available rivile contacts codes
            for contact in aList["N08"]:
                rivile_contacts_codes.append(str(contact["N08_KODAS_KS"]))

            diffrence = [i for i in rivile_contacts_codes if i not in odoo_contact_codes]
      
            if diffrence:
                # for diff in diffrence:
                    vals = {}
                    for contact in aList["N08"]:
                        # if contact["N08_KODAS_KS"] == diff:
                        # Rivile contact code
                            contact_code = str(contact["N08_KODAS_KS"])
                            print('contact code', contact_code)
                            if contact_code in diffrence:
                                #Contact name
                                client_name = contact["N08_PAV"]
                                # Contact email
                                email = contact["N08_E_MAIL"]
                                # Contact phone
                                phone = contact["N08_TEL"]
                                # Contact mobile phone
                                mobile_phone = contact["N08_MOB_TEL"]
                                # Contact address
                                address = contact["N08_ADR"]
                                # Contact TAX ID
                                tax_id = contact["N08_PVM_KODAS"]

                                # The address from Rivile
                                address = contact["N08_ADR"]
                                separated_address = address.split(',')
                                street = str(separated_address[0])
                                street2 = separated_address[1]
                                city = separated_address[2]
                                state_name = separated_address[3]
                                state_id = self.env['res.country.state'].search([('name', '=', state_name)])
                                zip = separated_address[4]
                                country_name = separated_address[5]
                                country_id = self.env['res.country'].search([('name', '=', country_name)])

                                vals = {
                                "name": client_name,
                                "email": email,
                                "phone": phone,
                                "mobile": mobile_phone,
                                "vat": tax_id,
                                "street": street,
                                "street2": street2,
                                "city": city,
                                "state_id": state_id.id,
                                "zip": zip,
                                "country_id": country_id.id,
                                "unique_code": contact_code
                            }
                                for contact in self.env['res.partner'].search([]):
                                    print('contact', contact)
                                    if contact.unique_code:
                                        existing_product = self.env['res.partner'].search([('id','!=',self.id),('unique_code','=',contact_code)])
                                        print('exist', existing_product)
                                        if not existing_product:
                                            contact.with_context(test1 = 'test1').create(vals)
                            else:
                                for contact in aList["N08"]:
                                    # Rivile contact code
                                    contact_code = str(contact["N08_KODAS_KS"])
                                    # #Contact name
                                    client_name = contact["N08_PAV"]
                                    # Contact email
                                    email = contact["N08_E_MAIL"]
                                    # Contact phone
                                    phone = contact["N08_TEL"]
                                    # Contact mobile phone
                                    mobile_phone = contact["N08_MOB_TEL"]
                                    # Contact address
                                    address = contact["N08_ADR"]
                                    # Contact TAX ID
                                    tax_id = contact["N08_PVM_KODAS"]

                                    # The address path
                                    address = contact["N08_ADR"]
                                    separated_address = address.split(',')
                                    street = str(separated_address[0])
                                    street2 = separated_address[1]
                                    city = separated_address[2]
                                    state_name = separated_address[3]
                                    state_id = self.env['res.country.state'].search([('name', '=', state_name)])
                                    zip = separated_address[4]
                                    country_name = separated_address[5]
                                    country_id = self.env['res.country'].search([('name', '=', country_name)])

                                    partner = self.env['res.partner'].search([('unique_code', '=', contact["N08_KODAS_KS"])])


                                    if "N08" in response.text and partner:
                                        print('client name', client_name)
                                        # Values from Rivile
                                        vals = {
                                            "name": client_name,
                                            "email": email, # print('inside function',self)
                                            "phone": phone,
                                            "mobile": mobile_phone,
                                            "vat": tax_id,
                                            "street": street,
                                            "street2": street2,
                                            "city": city,
                                            "state_id": state_id,
                                            "zip": zip,
                                            "country_id": country_id
                                        }
                                        # Edit values in Odoo
                                        
                                        for contact in self.env['res.partner'].search([('unique_code', '=', contact["N08_KODAS_KS"])]):
                                            # print('contact', contact)
                                            if contact.unique_code:
                                                existing_product = self.env['res.partner'].search([('unique_code','=',contact_code)])
                                                print('exist', existing_product)
                                                if existing_product:
                                                    print('testukass')
                                                    contact.with_context(test = 'test').write(vals)

            else:
                print('kontaktai odoo ir rivile sutampa')
                for contact in aList["N08"]:
                    # Rivile contact code
                    contact_code = str(contact["N08_KODAS_KS"])
                    # #Contact name
                    client_name = contact["N08_PAV"]
                    # Contact email
                    email = contact["N08_E_MAIL"]
                    # Contact phone
                    phone = contact["N08_TEL"]
                    # Contact mobile phone
                    mobile_phone = contact["N08_MOB_TEL"]
                    # Contact address
                    address = contact["N08_ADR"]
                    # Contact TAX ID
                    tax_id = contact["N08_PVM_KODAS"]

                    # The address path
                    address = contact["N08_ADR"]
                    separated_address = address.split(',')
                    street = str(separated_address[0])
                    street2 = separated_address[1]
                    city = separated_address[2]
                    state_name = separated_address[3]
                    state_id = self.env['res.country.state'].search([('name', '=', state_name)])
                    zip = separated_address[4]
                    country_name = separated_address[5]
                    country_id = self.env['res.country'].search([('name', '=', country_name)])

                    partner = self.env['res.partner'].search([('unique_code', '=', contact["N08_KODAS_KS"])])


                    if "N08" in response.text and partner:
                        print('client name', client_name)
                        # Values from Rivile
                        vals = {
                            "name": client_name,
                            "email": email, # print('inside function',self)
                            "phone": phone,
                            "mobile": mobile_phone,
                            "vat": tax_id,
                            "street": street,
                            "street2": street2,
                            "city": city,
                            "state_id": state_id,
                            "zip": zip,
                            "country_id": country_id
                        }
                        # Edit values in Odoo
                        
                        for contact in self.env['res.partner'].search([('unique_code', '=', contact["N08_KODAS_KS"])]):
                            # print('contact', contact)
                            if contact.unique_code:
                                existing_product = self.env['res.partner'].search([('unique_code','=',contact_code)])
                                print('exist', existing_product)
                                if existing_product:
                                    print('testukass')
                                    contact.with_context(test = 'test').write(vals)
      
                
                        

           