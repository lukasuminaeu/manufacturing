# -*- coding: utf-8 -*-


from venv import create
from odoo import models, fields, api
from datetime import datetime
from datetime import timedelta
from odoo.exceptions import UserError
import xml.etree.ElementTree as ET
import json
from requests.auth import HTTPBasicAuth

 
import requests
# current date and time


class ProductPricelistRivile(models.Model):
    _inherit = "product.pricelist.item"

    def write(self, vals):
        res = super(ProductPricelistRivile, self).write(vals)
        if 'test' not in self._context:
            self.create_pricelist_odoo_to_rivile()
        return res

    @api.model
    def create(self, vals): 
        res = super(ProductPricelistRivile, self).create(vals)
        if 'test' not in self._context:
            res.create_pricelist_odoo_to_rivile()
        return res

    def create_pricelist_odoo_to_rivile(self):
        now = datetime.now() + timedelta(hours=2) 
        formatted_time = now.strftime("%Y-%m-%d %H:%M") 
        for rec in self:
            riviles_kodas = self.product_tmpl_id.default_code
            if riviles_kodas:
                # Pricelist price
                pricelist_price = rec.fixed_price
                # Pricelist id
                pricelist_id = rec.pricelist_id.id
                # Pricelist start date
                # if rec.date_start:
                #     pricelist_start_date = rec.date_start
                # else:
                #     pricelist_start_date = formatted_time
                # Get Rivile pricelist type
                if pricelist_id == 1:
                    rivile_pricelist_type = "A"
                elif pricelist_id == 2:
                    rivile_pricelist_type = "B"
                elif pricelist_id == 3:
                    rivile_pricelist_type = "C"

                reqUrl = "https://api.manorivile.lt/client/v2"
                headersList = {
                "Accept": "application/json",
                "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
                "Content-Type": "application/json" 
                }
                # API request to get information about product price
                payload = json.dumps({
                    "method": "GET_N32_LIST",
                    "params": {
                        "fil": "n32_kodas_ps='{}' and N32_TIPAS='{}'".format(riviles_kodas, rivile_pricelist_type)
                    }
                })

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)
                
                aList = json.loads(response.text)

                if aList:
                    payload = json.dumps({
                        "method": "EDIT_N32",
                        "params": {
                            "oper": "U"
                        },
                        "data": {
                            "N32": {
                                "N32_KODAS_PS": riviles_kodas,
                                "N32_KODAS_US": "VNT ",
                                "N32_TIPAS": rivile_pricelist_type,
                                "N32_G_DATE": '2015-09-09',
                                "N32_KAINA1": pricelist_price
                            }
                        }
                    })
                    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                    if not response.status_code == 200:
                        raise UserError(response.text)
                else:
                    payload = json.dumps({
                        "method": "EDIT_N32",
                        "params": {
                            "oper": "I"
                        },
                        "data": {
                            "N32": {
                                "N32_KODAS_PS": riviles_kodas,
                                "N32_KODAS_US": "VNT ",
                                "N32_TIPAS": rivile_pricelist_type,
                                "N32_G_DATE": '2015-09-09',
                                "N32_KAINA1": pricelist_price
                            }
                        }
                    })
                    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                    if not response.status_code == 200:
                        raise UserError(response.text)
    

    def update_pricelist_rivile_to_odoo(self):
        now = datetime.now() + timedelta(hours=2) 
        formatted_time = now.strftime("%Y-%m-%d %H:%M")
        scheduled_action = self.env['ir.cron'].search([('id', '=', 28)])
        scheduled_time_plus_2hrs = scheduled_action._origin.lastcall + timedelta(hours=2)
        scheduled_last_time = scheduled_time_plus_2hrs.strftime("%Y-%m-%d %H:%M")

        aList = []

        products = self.env['product.template'].search([])
        for product in products:

            reqUrl = "https://api.manorivile.lt/client/v2"

            headersList = {
            "Accept": "application/json",
            "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
            "Content-Type": "application/json" 
            }
            print('scheduled lastcall', scheduled_last_time)
            print('formatted time', formatted_time)
            payload = json.dumps({
                "method": "GET_N32_LIST",
                "params": {
                "fil": "n32_kodas_ps in (select distinct '{}' from RGI_N32_TRIGGER_TABLE where N32_r_date>'{}' and N32_r_date<'{}')".format(product.default_code, scheduled_last_time, formatted_time)
                # "fil": "n32_kodas_ps in (select distinct '{}' from RGI_N32_TRIGGER_TABLE where N32_r_date>'{}')".format(rec.x_studio_riviles_kodas, scheduled_action._origin.lastcall)

                # FOR DEVELOPMENT ONLY
                # "fil": "n32_kodas_ps in (select distinct '{}' from RGI_N32_TRIGGER_TABLE where N32_r_date>'{}' and N32_r_date<'{}')".format(product.default_code, '2022-10-31 17:00', formatted_time)
                # "fil": "n32_kodas_ps in (select distinct '{}' from RGI_N32_TRIGGER_TABLE where N32_r_date>'{}' and N32_r_date<'{}')".format(product.default_code, '2022-11-03 12:00', '2022-11-04 12:53')
                    }
                })
            response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            if not response.status_code == 200:
                raise UserError(response.text)
            # API Response
            pricelist_rivile = json.loads(response.text)
            
            if pricelist_rivile:
                # Check if dictionary has list inside, that means more than one pricelist are returned and need to loop.
                if isinstance(pricelist_rivile["N32"], list) == True:
                    vals = {}
                    for pricelist in pricelist_rivile["N32"]:
                        riviles_kodas = pricelist["N32_KODAS_PS"]
                        pricelist_type = pricelist["N32_TIPAS"]
                        pricelist_price = pricelist["N32_KAINA1"]
                        product_template = self.env['product.template'].search([('default_code','=', riviles_kodas)])
                        if pricelist_type == "A":
                            vals = {
                                "pricelist_id": 1,
                                "applied_on": '1_product',
                                "product_tmpl_id": product_template.id,
                                "fixed_price": pricelist_price
                            }
                        elif pricelist_type == "B":
                            vals = {
                                "pricelist_id": 2,
                                "applied_on": '1_product',
                                "product_tmpl_id": product_template.id,
                                "fixed_price": pricelist_price
                            }
                        elif pricelist_type == "C":
                            vals = {
                                "pricelist_id": 3,
                                "applied_on": '1_product',
                                "product_tmpl_id": product_template.id,
                                "fixed_price": pricelist_price
                            }
                        pricelist_item = self.env['product.pricelist.item'].search([('product_tmpl_id', '=', product_template.id), ('pricelist_id', '=', vals['pricelist_id'])])

                        if not pricelist_item:
                            # Create pricelist in Odoo
                            pricelist_item.with_context(test = 'test').create(vals)
                        else:
                            # Update existing Odoo products pricelists
                            pricelist_item.with_context(test = 'test').update(vals)

                        # pricelist_item.with_context(test = 'test').update(vals)
                        # Update existing Odoo products pricelists
                        # create_pricelist = self.env['product.pricelist.item'].write(vals)
                        # self.env['product.pricelist.item'].write(vals)
                else:

                    vals = {}
                    riviles_kodas = pricelist_rivile["N32"]["N32_KODAS_PS"]
                    pricelist_type = pricelist_rivile["N32"]["N32_TIPAS"]
                    pricelist_price = pricelist_rivile["N32"]["N32_KAINA1"]
                    product_template = self.env['product.template'].search([('default_code','=', riviles_kodas)])
                    if pricelist_type == "A":
                        vals = {
                            "pricelist_id": 1,
                            "applied_on": '1_product',
                            "product_tmpl_id": product_template.id,
                            "fixed_price": pricelist_price
                        }
                    elif pricelist_type == "B":
                        vals = {
                            "pricelist_id": 2,
                            "applied_on": '1_product',
                            "product_tmpl_id": product_template.id,
                            "fixed_price": pricelist_price
                        }
                    elif pricelist_type == "C":
                        vals = {
                            "pricelist_id": 3,
                            "applied_on": '1_product',
                            "product_tmpl_id": product_template.id,
                            "fixed_price": pricelist_price
                        }
                    
                    pricelist_item = self.env['product.pricelist.item'].search([('product_tmpl_id', '=', product_template.id), ('pricelist_id', '=', vals['pricelist_id'])])
                    if not pricelist_item:
                        # Create pricelist in Odoo
                        pricelist_item.with_context(test = 'test').create(vals)
                    else:
                        # Update existing Odoo products pricelists
                        pricelist_item.with_context(test = 'test').update(vals)
            
     







                


    
