# -*- coding: utf-8 -*-


from venv import create
from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError
import xml.etree.ElementTree as ET
import json
from requests.auth import HTTPBasicAuth
import requests
# current date and time
now = datetime.now() 


class SalesRivile(models.Model):
    _inherit = 'sale.order'


    def action_confirm(self):
        for rec in self:
            aList = []
            reqUrl = "https://api.manorivile.lt/client/v2"

            headersList = {
            "Accept": "application/json",
            "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
            "Content-Type": "application/json" 
            }

            payload = json.dumps({
                "method": "GET_I06_LIST",
                "params": {
                    "list": "A",
                    "fil": "I06_DOK_NR='{}'".format(rec.name)
                }
            })

            response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            if not response.status_code == 200:
                    raise UserError(response.text)
            
            aList = json.loads(response.text)
    
            if aList:
                raise UserError("Dokumentas Rivile sistemoje su tokiu pavadinimu jau egzistuoja!")
            else:
                # define empty dictionary
                my_dict = {}
                # define empty data list
                data = []

                date_order = rec.date_order.strftime("%Y-%m-%d")
                client_code = rec.partner_id.unique_code


                order_lines = rec.order_line


                for line in order_lines:
                    # product name (code)
                    procuct_name = line.name
                    # product rivile code
                    product_rivile_code = line.product_id.default_code
                    # product quantity done
                    product_qty = line.product_uom_qty
                    # proudct price without taxes
                    product_price_wo = line.price_subtotal
                    # product price with taxes
                    product_price_w = product_price_wo + (product_price_wo * (line.tax_id.amount / 100))
                    # tax amount
                    amount_tax = product_price_wo * (line.tax_id.amount / 100)
                    # if quantity is less than 1, create dictionary only with quantity 1 or above
                    my_dict = {
                        "I07_TIPAS": 1,
                        "I07_KODAS_IS": "TESTPARD",
                        "I07_KODAS": product_rivile_code,
                        "I07_KAINA_BE": product_price_wo,
                        "I07_KAINA_SU": product_price_w,
                        "I07_PVM": amount_tax,
                        "I07_SUMA": product_price_wo,
                        "I07_KODAS_US": "VNT",
                        "I07_KIEKIS": product_qty,
                        "I07_KODAS_US_P": "VNT",
                        "I07_KODAS_US_A": "VNT"
                    }
                    # append dictionary(-ies) in data list        
                    if len(my_dict) == 0:
                        return
                    else:
                        data.append(my_dict)
                payload = json.dumps({
                    "method": "EDIT_I06_FULL",
                    "params": {
                        "errorAction": "CONTINUE"
                    },
                    "data": {
                        "I06": {
                            "I06_KODAS_KS": client_code,
                            "I06_OP_TIP": 51,
                            "I06_PVM_TIP": 1,
                            "I06_DOK_NR": rec.name,
                            "I06_OP_DATA": date_order,
                            "I06_APRASYMAS1": rec.opportunity_id.id,
                            "I07": data
                        }
                    }
                })

                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)

        res = super(SalesRivile, self).action_confirm()
        return res

    # def sales_odoo_to_rivile(self):
    #     for rec in self:
    #         aList = []
    #         reqUrl = "https://api.manorivile.lt/client/v2"

    #         headersList = {
    #         "Accept": "application/json",
    #         "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
    #         "Content-Type": "application/json" 
    #         }

    #         payload = json.dumps({
    #             "method": "GET_I06_LIST",
    #             "params": {
    #                 "list": "A",
    #                 "fil": "I06_DOK_NR='{}'".format(rec.name)
    #             }
    #         })

    #         response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            
    #         aList = json.loads(response.text)
    #         if aList:
    #             print('test aList',aList)
    #             raise UserError("Dokumentas Rivile sistemoje su tokiu pavadinimu jau egzistuoja!")
    #             # atnaujint galimybes turbut kad nera, nebent per atskirus metodus, EDIT_I06 ir EDIT_I07

    #         else:
    #             # define empty dictionary
    #             my_dict = {}
    #             # define empty data list
    #             data = []

    #             date_order = rec.date_order.strftime("%Y-%m-%d")
    #             client_code = rec.partner_id.unique_code
    #             # amount_untaxed = self.amount_untaxed
    #             # amount_total = self.amount_total
    #             # amount_tax = self.amount_tax

    #             order_lines = rec.order_line

    #             # if len(order_lines) > 1:
    #             for line in order_lines:
    #                 # product name (code)
    #                 procuct_name = line.name
    #                 # product quantity done
    #                 product_qty = line.product_uom_qty
    #                 # proudct price without taxes
    #                 product_price_wo = line.price_subtotal
    #                 # product price with taxes
    #                 product_price_w = product_price_wo + (product_price_wo * (line.tax_id.amount / 100))
    #                 # tax amount
    #                 amount_tax = product_price_wo * (line.tax_id.amount / 100)
    #                 # if quantity is less than 1, create dictionary only with quantity 1 or above
    #                 my_dict = {
    #                     "I07_TIPAS": 1,
    #                     "I07_KODAS_IS": "TESTPARD",
    #                     "I07_KODAS": procuct_name,
    #                     "I07_KAINA_BE": product_price_wo,
    #                     "I07_KAINA_SU": product_price_w,
    #                     "I07_PVM": amount_tax,
    #                     "I07_SUMA": product_price_wo,
    #                     "I07_KODAS_US": "VNT",
    #                     "I07_KIEKIS": product_qty,
    #                     "I07_KODAS_US_P": "VNT",
    #                     "I07_KODAS_US_A": "VNT",
    #                 }
    #                 # append dictionary(-ies) in data list        
    #                 if len(my_dict) == 0:
    #                     return
    #                 else:
    #                     data.append(my_dict)
                
    #             print('data', data)
    #             payload = json.dumps({
                    
    #                 "method": "EDIT_I06_FULL",
    #                 "params": {
    #                     "errorAction": "CONTINUE"
    #                 },
    #                 "data": {
    #                     "I06": {
    #                         "I06_KODAS_KS": client_code,
    #                         "I06_OP_TIP": 51,
    #                         "I06_PVM_TIP": 1,
    #                         "I06_DOK_NR": rec.name,
    #                         "I06_OP_DATA": date_order,
    #                         "I06_APRASYMAS1": rec.opportunity_id.id,
    #                         "I07": data
    #                     }
    #                 }
    #             })
    #             # DAROM KOLKAS TIK ODOO TO RIVILE VIDINIO DOK SUKURIMA, ANT CONFIRM QUOTATION

    #             response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
    #             if not response.status_code == 200:
    #                 raise UserError(response.text)

    

    # def sales_rivile_to_odoo(self):
    #     for rec in self:
    #         reqUrl = "https://api.manorivile.lt/client/v2"

    #         headersList = {
    #         "Accept": "application/json",
    #         "ApiKey": "PIHUUQX.Ur1MY7UlSwWjsZdfoKc4I3UoY6D5K3PWOcMzw0fk",
    #         "Content-Type": "application/json" 
    #         }

    #         # payload = json.dumps({
    #         #     "method": "GET_I06_LIST",
    #         #     "params": {
    #         #         "list": "A",
    #         #         "fil": "I06_DOK_NR='TEST3'"
    #         #     }
    #         # })
    #         payload = json.dumps({
    #             "method": "GET_I06_LIST",
    #             "params": {
    #                 "list": "H",
    #                 "fil": "I06_DOK_NR='{}'".format(rec.name)
    #             }
    #         })

    #         response = requests.request("POST", reqUrl, data=payload,  headers=headersList)


    #         aList = json.loads(response.text)


            # PACIUOSE ORDERIUOSE, REIKTU ANT ACTION, KAD BUTU FUNKCIJA SITA
            # TIKRINAM AR YRA TOKS ODOO SISTEMOJE DOKUMENTAS, JEIGU NE KURIAM NAUJA QUOTATION
            # APACIOJ YRA KUR TIKRINA AR VIENAS PRODUKTAS AR DAUGIAU, PAGAL TA LOGIKA REIKTU
            # KURTI NAUJA ODOO SISTEMOJE DOKUMENTA

            # print('RES STATUS', response.text)
            # print('TEST PYTHON LIST', aList["I0"]["I06_DOK_NR"])
            
        

            # my_dict = {}

            # order_line = [
            #     (0,0,{
            #         'product_id': 4,
            #         'product_uom_qty': 4
            #     })
            # ]

            


            # if isinstance(aList["I06"]["I07"], list) == True:
            #     for items in aList["I06"]["I07"]:
            #         product_name = items["I07_KODAS"]
            #         product_id = rec.env['product.template'].search([('name','=', product_name)]).id
            #         product_uom_qty = items["I07_KIEKIS"]
            #         # partner_id = items["I06_KODAS_KS"]

            #         my_dict.append(product_id)
            #         my_dict.append(product_uom_qty)
            #         # print('TEST TEST',my_dict)


            # else:
            #     product_name = aList["I06"]["I07"]["I07_KODAS"]
            #     product_id = rec.env['product.template'].search([('name','=', product_name)]).id
            #     product_uom_qty = aList["I06"]["I07"]["I07_KIEKIS"]
            #     partner_id = aList["I06"]["I06_KODAS_KS"]
            #     my_dict["product_id"] = product_id
            #     my_dict["product_uom_qty"] = product_uom_qty


                # print('test product id', my_dict)
                # print('nera listo, reiskia vienas produktas', aList["I06"]["I07"]["I07_KODAS"])
            
        
            # sale_order = self.env['sale.order'].create({
            #     'partner_id': 7,
            #     'partner_invoice_id': 7,
            #     'partner_shipping_id': 7,
            #     'order_line': order_line,
            #     'pricelist_id': 1,
            #     'picking_policy': 'direct',
            # })





