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
from datetime import datetime, timedelta



class ProductTemplateRivile(models.Model):
    _inherit = 'product.template'

    # x_studio_riviles_kodas = fields.Char(string="Rivilės kodas", store=True)



    def write(self, vals):
        res = super(ProductTemplateRivile, self).write(vals)
        if 'test' not in self._context:
            self.product_create_in_rivile()
        # self.product_price_odoo_to_rivile()
        # self.product_info_odoo_to_rivile()
        return res

    @api.model
    def create(self, vals): 
        res = super(ProductTemplateRivile, self).create(vals)
        if 'test' not in self._context:
            res.product_create_in_rivile()
        return res


     # Function for product price update in Odoo
    def product_price_rivile_to_odoo(self):
        for rec in self:
            vals = {}

            riviles_kodas = rec.default_code
            if riviles_kodas:
                reqUrl = "https://api.manorivile.lt/client/v2"
                headersList = {
                "Accept": "application/json",
                "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
                "Content-Type": "application/json" 
                }
                # API request to get information about product price
                payload = json.dumps({
                    "method": "GET_I33_LIST",
                    "params": {
                        # "fil": "i33_kodas_ps='table'"
                        "fil": "i33_kodas_ps='{}'".format(riviles_kodas)
                    }
                })

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError('Product Price Update',response.text)
                
                aList = json.loads(response.text)

                # Product price
                if "I33_KAINA" in aList["I33"]:
                    vals["list_price"] = aList["I33"]["I33_KAINA"]
                # Edit values in Odoo
                rec.write(vals)
    # Function for product price update in Rivile
    def product_price_odoo_to_rivile(self):
        for rec in self:
            riviles_kodas = rec.default_code
            if riviles_kodas:
                # Product name
                product_name = rec.name
                # Product price
                product_price = rec.list_price
                reqUrl = "https://api.manorivile.lt/client/v2"
                headersList = {
                "Accept": "*/*",
                "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
                "Content-Type": "application/json" 
                }
                # API request to get information about product price
                payload = json.dumps({
                    "method": "GET_I33_LIST",
                    "params": {
                        
                        # "fil": "i33_kodas_ps='table'"
                        "fil": "i33_kodas_ps='{}'".format(riviles_kodas)
                    }
                })

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)
                # If there is key "I33" update existing product price
                if "I33" in response.text:
                    payload = json.dumps({
                        "method": "EDIT_I33",
                        "params": {
                            "oper": "U"
                        },
                        "data": {
                            "I33": {
                                "I33_KODAS_PS": riviles_kodas,
                                "I33_KODAS_IS": "TESTPARD",
                                "I33_KODAS_US": "VNT",
                                "I33_KAINA":product_price
                            }
                        }
                    })

                    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                    if not response.status_code == 200:
                        raise UserError(response.text)
                else:
                    # If there is no key "I33" create new record in Rivile about product price
                    payload = json.dumps({
                        "method": "EDIT_I33",
                        "params": {
                            "oper": "I"
                        },
                        "data": {
                            "I33": {
                                "I33_KODAS_PS": riviles_kodas,
                                "I33_KODAS_IS": "TESTPARD",
                                "I33_KODAS_US": "VNT",
                                "I33_KAINA": product_price
                            }
                        }
                    })

                    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                    if not response.status_code == 200:
                        raise UserError(response.text)
    # Function to send product info from Odoo to Rivile
    def product_info_odoo_to_rivile(self):
        for rec in self:
            riviles_kodas = rec.default_code
            if riviles_kodas:
                # Product name
                product_name = rec.name
                # Product type
                product_type = rec.detailed_type
                if product_type == 'product':
                    product_type_for_rivile = 1
                elif product_type == 'service':
                    product_type_for_rivile = 2

                

                reqUrl = "https://api.manorivile.lt/client/v2"
                headersList = {
                "Accept": "*/*",
                "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
                "Content-Type": "application/json" 
                }
                # API request to get information about product price
                payload = json.dumps({
                    "method": "GET_N17_LIST",
                    "params": {
                        "list": "A",
                        "fil": "n17_kodas_ps='{}'".format(riviles_kodas) 
                    }
                })

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError('Product Info Update',response.text)
            
                if "N17" in response.text:
                    payload = json.dumps({
                        "method": "EDIT_N17",
                        "params": {
                            "oper": "U"
                        },
                        "data": {
                            "N17": {
                                "N17_KODAS_PS": riviles_kodas,
                                "N17_TIPAS": product_type_for_rivile,
                                "N17_PAV": product_name,
                                "N17_KODAS_DS": "PR001",
                                "N17_KODAS_US": "VNT"
                            }
                        }
                    })


                    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                    if not response.status_code == 200:
                        raise UserError(response.text)
                else:
                    raise UserError("Tokio produkto Rivile sistemoje nėra!")     
        # Function to get product info from Rivile to Odoo
    def product_info_rivile_to_odoo(self):
        vals = {}
        for rec in self:
            # Contact code/ID
            riviles_kodas = rec.default_code
            # Check if product has RIVILE CODE in Odoo, if so - update product 
            if riviles_kodas:

                reqUrl = "https://api.manorivile.lt/client/v2"

                headersList = {
                "Accept": "application/json",
                "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
                "Content-Type": "application/json" 
                }

                payload = json.dumps({
                    "method": "GET_N17_LIST",
                    "params": {
                        "list": "A",
                        "fil": "N17_KODAS_PS='{}'".format(riviles_kodas)
                        # "fil": "N17_KODAS_PS='chair'"
                    }
                })

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)

                # print('RES STATUS', response.text)

                aList = json.loads(response.text)

                # Product name
                if "N17_PAV" in aList["N17"]:
                    vals["name"] = aList["N17"]["N17_PAV"]
                # Product code in Rivile
                if "N17_KODAS_PS" in aList["N17"]:
                    vals["default_code"] = aList["N17"]["N17_KODAS_PS"]
                # Product price
                if "I33" in aList["N17"]:
                    vals["list_price"] = aList["N17"]["I33"]["I33_KAINA"]

                # Values from Rivile
                # vals = {
                #     "name": product_name,
                #     "list_price": product_price,


                # }
                # # Contact email
                # email = aList["N08"]["N08_E_MAIL"]
                # # Contact phone
                # phone = aList["N08"]["N08_TEL"]
                # # Contact mobile phone
                # mobile_phone = aList["N08"]["N08_MOB_TEL"]
                # # Contact address
                # address = aList["N08"]["N08_ADR"]

                # # Problema su adresu, Odoo sistemoje viskas eina i atskirus fieldus, street, street1, city ir pan,
                # #  is Rivile mes gaunam kaip stringa, kaip patalpinti i Odoo adresa?

                # Edit values in Odoo
                # for record in self:
                rec.write(vals)



    def product_create_in_rivile(self):

        for rec in self:
            riviles_kodas = rec.default_code
            if riviles_kodas:
                # Product name
                product_name = rec.name
                # Product type
                product_type = rec.detailed_type
                if product_type == 'product':
                    product_type_for_rivile = 1
                elif product_type == 'service':
                    product_type_for_rivile = 2

                reqUrl = "https://api.manorivile.lt/client/v2"
                headersList = {
                "Accept": "*/*",
                "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
                "Content-Type": "application/json" 
                }
                # API request to get information about product price
                payload = json.dumps({
                    "method": "GET_N17_LIST",
                    "params": {
                        "list": "H",
                        "fil": "n17_kodas_ps='{}'".format(riviles_kodas) 
                    }
                })

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError('Product Info Update',response.text)
            
                if "N17" in response.text:
                    payload = json.dumps({
                        "method": "EDIT_N17",
                        "params": {
                            "oper": "U"
                        },
                        "data": {
                            "N17": {
                                "N17_KODAS_PS": riviles_kodas,
                                "N17_TIPAS": product_type_for_rivile,
                                "N17_PAV": product_name,
                                "N17_KODAS_DS": "PR001",
                                "N17_KODAS_US": "VNT"
                            }
                        }
                    })

                    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                    if not response.status_code == 200:
                        raise UserError(response.text)
                else:
                    payload = json.dumps({
                    "method": "EDIT_N17",
                    "params": {
                        "oper": "I"
                    },
                    "data": {
                        "N17": {
                            "N17_KODAS_PS": riviles_kodas,
                            "N17_TIPAS": product_type_for_rivile,
                            "N17_PAV": product_name,
                            "N17_KODAS_DS": "PR001",
                            "N17_KODAS_US": "VNT"
                        }
                    }
                })

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)
        

    def product_create_rivile_to_odoo(self):
        aList = []
        diffrence = []

        now = datetime.now() + timedelta(hours=2) 
        formatted_time = now.strftime("%Y-%m-%d %H:%M")
        scheduled_action = self.env['ir.cron'].search([('id', '=', 27)])
        scheduled_time_plus_2hrs = scheduled_action._origin.lastcall + timedelta(hours=2)
        scheduled_last_time = scheduled_time_plus_2hrs.strftime("%Y-%m-%d %H:%M")
        
        all_odoo_products = self.env['product.template'].search([])
        for odoo_product in all_odoo_products:
            reqUrl = "https://api.manorivile.lt/client/v2"

            headersList = {
            "Accept": "application/json",
            "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
            "Content-Type": "application/json" 
            }

            payload = json.dumps({
                "method": "GET_N17_LIST",
                "params": {
                    "list": "H"
                    # "fil": "N17_kodas_ps in (select distinct '{}' from RGI_N17_TRIGGER_TABLE where N17_r_date>'{}')".format(odoo_product.default_code,'2022-11-03 10:00')
                }
            })

            response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            if not response.status_code == 200:
                raise UserError(response.text)

            aList = json.loads(response.text)
            # print('aList', aList)

            if aList:
                
                rivile_products = []
                # Get all available products in Odoo
                odoo_products = []
                for product in self.env['product.template'].search([]):
                        odoo_products.append(product.default_code)
                # Check if dictionary has list inside, that means more than one pricelist are returned and need to loop.
                if isinstance(aList["N17"], list) == True:
                    # Get products from Rivile
                    for rivile_prod in aList["N17"]:
                        rivile_products.append(rivile_prod["N17_KODAS_PS"])
                else:
                    # Get product from Rivile
                    rivile_products.append(aList["N17"]["N17_KODAS_PS"])

                diffrence = [i for i in rivile_products if i not in odoo_products]
 

                vals_product = {}

                if diffrence:
                    if isinstance(aList["N17"], list) == True:
                        for diff in diffrence:
                            for item in aList["N17"]:
                                if item["N17_KODAS_PS"] == diff:
                                    vals_product = {
                                            "name": item["N17_PAV"],
                                            "list_price": 0,
                                            "detailed_type": "product",
                                            "default_code": item["N17_KODAS_PS"]
                                        }
                            # Create new product in Odoo
                            products = self.env['product.template'].search([('default_code', '=', diff)])
                            if not products:
                                products.with_context(test = 'test').create(vals_product)
                            else:
                                products.with_context(test = 'test').write(vals_product)
                        
                            # record = self.env['product.template'].create(vals_product)
                    else:
                        for diff in diffrence:
                            if aList["N17"]["N17_KODAS_PS"] == diff:
                                vals_product = {
                                        "name": aList["N17"]["N17_PAV"],
                                        "list_price": 0,
                                        "detailed_type": "product",
                                        "default_code": aList["N17"]["N17_KODAS_PS"]
                                    }
                        # Create new product in Odoo
                        products = self.env['product.template'].search([('default_code', '=', aList["N17"]["N17_KODAS_PS"])])
                        if not products:
                            products.with_context(test = 'test').create(vals_product)
                        else:
                            products.with_context(test = 'test').write(vals_product)
                else:
                    payload = json.dumps({
                        "method": "GET_N17_LIST",
                        "params": {
                            "list": "H",
                            "fil": "n32_kodas_ps in (select distinct '{}' from RGI_N32_TRIGGER_TABLE where N32_r_date>'{}' and N32_r_date<'{}')".format(product.default_code, scheduled_action._origin.lastcall, formatted_time)
                            # "fil": "N17_kodas_ps in (select distinct '{}' from RGI_N17_TRIGGER_TABLE where N17_r_date>'{}')".format(odoo_product.default_code,'2022-11-03 14:58')
                        }
                    })

                    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                    if not response.status_code == 200:
                        raise UserError(response.text)

                    aList = json.loads(response.text)

                    if aList:
                            vals = {}
                            vals = {
                                "name": aList["N17"]["N17_PAV"],
                                "list_price": 0,
                                "detailed_type": "product",
                                "default_code": aList["N17"]["N17_KODAS_PS"]
                            }
                            # Create new product in Odoo
                            products = self.env['product.template'].search([('default_code', '=', aList["N17"]["N17_KODAS_PS"])])
                            if products:
                                products.with_context(test = 'test').write(vals)

                            
                        
                            
                            

            

                
                        




           
           

        



        



        