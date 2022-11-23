# -*- coding: utf-8 -*-


from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import json
from requests.auth import HTTPBasicAuth
import requests
# current date and time
now = datetime.now() 


class StockBackorderConfirmationInherit(models.TransientModel):
    _inherit = "stock.backorder.confirmation" 


    

    def process(self):

        # Get current stock picking quantity_done and product_uom_qty values
        # for picking in self.pick_ids.move_ids_without_package:
        #     current_product_qty = picking.quantity_done
        # for picking in self.pick_ids.move_ids_without_package:
        #     demand = picking.product_uom_qty
        # res = super(StockBackorderConfirmationInherit, self).process()
        aList = []
        # define empty dictionary
        my_dict = {}
        # define empty data list
        data = []
        # Sale order id
        sale_id = self.pick_ids.sale_id

        if self.pick_ids.backorder_id:
            dok_nr = self.pick_ids.origin + '_' + str(self.pick_ids.backorder_id.id)
        else:
            dok_nr = sale_id.name
        
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
                "fil": "I06_DOK_NR='{}'".format(dok_nr)
            }
        })

        response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
        if not response.status_code == 200:
            raise UserError(response.text)

        aList = json.loads(response.text)

        i06_kodas_po = aList["I06"]["I06_KODAS_PO"]

        sale_order_line = sale_id.order_line
        move_lines = self.pick_ids.move_ids_without_package

        for index, (line, picking) in enumerate(zip(sale_order_line, move_lines), 1):



        # for index, line in enumerate(sale_id.order_line, 1):
        #     for picking in self.pick_ids.move_ids_without_package:
            current_product_qty = picking.quantity_done
            demand = picking.product_uom_qty
        
            
            
            
            product_rivile_code = line.product_id.default_code
            # Values for current Rivile document update
            current_product_price = line.price_unit
            current_price_without_taxes = current_product_price * current_product_qty
            current_product_taxes = (current_product_price * self.pick_ids.product_id.taxes_id.amount / 100) * current_product_qty
            current_price_with_taxes = current_price_without_taxes + current_product_taxes

            
            
            # Values for backorder/new document creation in Rivile
            product_qty = demand - current_product_qty
            product_price = line.price_unit
            price_without_taxes = product_price * product_qty
            product_taxes = (product_price * self.pick_ids.product_id.taxes_id.amount / 100) * product_qty
            price_with_taxes = price_without_taxes + product_taxes
            

            print('demand', demand, product_rivile_code)
            print('curr qty', current_product_qty, product_rivile_code)
            print('product qty, sitas turi eiti i nauja pardavimo dokumenta',product_qty, product_rivile_code)



            if i06_kodas_po:
                payload = json.dumps({
                    "method": "EDIT_I07",
                    "params": {
                        "oper": "U"
                    },
                    "data": {
                        "I07": {
                            "I07_KODAS_PO": i06_kodas_po,
                            "I07_EIL_NR": index,
                            "I07_TIPAS": 1,
                            "I07_KODAS_IS": "TESTPARD",
                            "I07_KODAS": product_rivile_code,
                            "I07_KAINA_BE": current_price_without_taxes,
                            "I07_KAINA_SU": current_price_with_taxes,
                            "I07_PVM": current_product_taxes,
                            "I07_SUMA": current_price_without_taxes,
                            "I07_KODAS_US": "VNT",
                            "I07_KIEKIS": current_product_qty,
                            "I07_KODAS_US_P": "VNT",
                            "I07_KODAS_US_A": "VNT"
                        }
                    }
                })
        
                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)

            my_dict = {
                "I07_TIPAS": 1,
                "I07_KODAS_IS": "TESTPARD",
                "I07_KODAS": product_rivile_code,
                "I07_KAINA_BE": price_without_taxes,
                "I07_KAINA_SU": price_with_taxes,
                "I07_PVM": product_taxes,
                "I07_SUMA": price_without_taxes,
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
        else:
            print('po for loop')
            payload = json.dumps({
                "method": "EDIT_I06",
                "params": {
                    "oper": "P"
                },
                "data": {
                    "I06": {
                        "I06_KODAS_PO": i06_kodas_po
                    }
                }
            })   

            response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            if not response.status_code == 200:
                raise UserError(response.text)
                
        payload = json.dumps({
            "method": "EDIT_I06_FULL",
            "params": {
                "errorAction": "CONTINUE"
            },
            "data": {
                "I06": {
                    "I06_KODAS_KS": self.pick_ids.partner_id.unique_code,
                    "I06_OP_TIP": 51,
                    "I06_PVM_TIP": 1,
                    "I06_DOK_NR": self.pick_ids.origin + '_' + str(self._origin.pick_ids.id),
                    "I06_OP_DATA": self.create_date.strftime("%Y-%m-%d"),
                    # "I06_APRASYMAS1": rec.opportunity_id.id,
                    "I07": data
                }
            }
        })

        response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
        if not response.status_code == 200:
            raise UserError(response.text)
        res = super(StockBackorderConfirmationInherit, self).process()
        # raise UserError('TESTAS')
        return res

    def process_cancel_backorder(self):
        for picking in self.pick_ids.move_ids_without_package:
            current_product_qty = picking.quantity_done
        res = super(StockBackorderConfirmationInherit, self).process_cancel_backorder()
        
        aList = []

        # Sale order id
        sale_id = self.pick_ids.sale_id

        if self.pick_ids.backorder_id:
            dok_nr = self.pick_ids.origin + '_' + str(self.pick_ids.backorder_id.id)
        else:
            dok_nr = sale_id.name
        
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
                "fil": "I06_DOK_NR='{}'".format(dok_nr)
            }
        })
        response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
        if not response.status_code == 200:
            raise UserError(response.text)

        aList = json.loads(response.text)

        i06_kodas_po = aList["I06"]["I06_KODAS_PO"]

        for index, line in enumerate(sale_id.order_line, 1):
            
            product_rivile_code = line.product_id.default_code
            # Values for current Rivile document update
            current_product_price = line.price_unit
            current_price_without_taxes = current_product_price * current_product_qty
            current_product_taxes = (current_product_price * self.pick_ids.product_id.taxes_id.amount / 100) * current_product_qty
            current_price_with_taxes = current_price_without_taxes + current_product_taxes

            if i06_kodas_po:
                payload = json.dumps({
                    "method": "EDIT_I07",
                    "params": {
                        "oper": "U"
                    },
                    "data": {
                        "I07": {
                            "I07_KODAS_PO": i06_kodas_po,
                            "I07_EIL_NR": index,
                            "I07_TIPAS": 1,
                            "I07_KODAS_IS": "TESTPARD",
                            "I07_KODAS": product_rivile_code,
                            "I07_KAINA_BE": current_price_without_taxes,
                            "I07_KAINA_SU": current_price_with_taxes,
                            "I07_PVM": current_product_taxes,
                            "I07_SUMA": current_price_without_taxes,
                            "I07_KODAS_US": "VNT",
                            "I07_KIEKIS": current_product_qty,
                            "I07_KODAS_US_P": "VNT",
                            "I07_KODAS_US_A": "VNT"
                        }
                    }
                })
        
                response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                if not response.status_code == 200:
                    raise UserError(response.text)
        else:
            
            payload = json.dumps({
                "method": "EDIT_I06",
                "params": {
                    "oper": "P"
                },
                "data": {
                    "I06": {
                        "I06_KODAS_PO": i06_kodas_po
                    }
                }
            })   

            response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            if not response.status_code == 200:
                raise UserError(response.text)
                      
        return res
    


class StockPickingRivile(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        for picking in self.move_ids_without_package:
            current_product_qty = picking.quantity_done
        # for picking in self.move_ids_without_package:
        #     demand = picking.product_uom_qty
        res = super(StockPickingRivile, self).button_validate()

        # check if it's backorder transfer or not
        if self.backorder_id:
            order_name = self.sale_id.name + '_' + str(self.backorder_id.id)
        else:
            order_name = self.sale_id.name

        if res == True:
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
                    "fil": "I06_DOK_NR='{}'".format(order_name)
                }
            })
            response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
            if not response.status_code == 200:
                raise UserError(response.text)
            
            aList = json.loads(response.text)

            i06_kodas_po = aList["I06"]["I06_KODAS_PO"]
            confirmed = aList["I06"]["I06_PERKELTA"]
            for move_line in self.move_lines:
                product_default_code = move_line.product_id.default_code
            if isinstance(aList["I06"]["I07"], list) == True:
                for item in aList["I06"]["I07"]:
                    rivile_product_qty = item["I07_KIEKIS"]
                    rivile_product_code = item["I07_KODAS"]
                if rivile_product_code.casefold() == product_default_code.casefold() and rivile_product_qty != current_product_qty  and current_product_qty != 0:
                    print('test pasikeites kiekis')
                else:
                    print('test list nepasikeites kieki, naudoti perkelima, tam kad nusirasytu kiekiai')

                    if i06_kodas_po and confirmed == 1:
                        payload = json.dumps({
                            "method": "EDIT_I06",
                            "params": {
                                "oper": "P"
                            },
                            "data": {
                                "I06": {
                                    "I06_KODAS_PO": i06_kodas_po
                                }
                            }
                        })   
                        response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                        if not response.status_code == 200:
                            raise UserError(response.text)
            else:

                if aList["I06"]["I07"]["I07_KODAS"].casefold() == product_default_code.casefold() and aList["I06"]["I07"]["I07_KIEKIS"] != current_product_qty  and current_product_qty != 0:
                    print('test pasikeites kiekis, delivery transferyje done kiekis nesutampa su pradiniu kiekiu')
                else:
                    print('test vienas nepasikeites kiekis, naudoti perkelima, tam kad nusirasytu kiekiai')
                    if i06_kodas_po and confirmed == 1:
                        payload = json.dumps({
                            "method": "EDIT_I06",
                            "params": {
                                "oper": "P"
                            },
                            "data": {
                                "I06": {
                                    "I06_KODAS_PO": i06_kodas_po
                                }
                            }
                        })   
                        response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
                        if not response.status_code == 200:
                            raise UserError(response.text)   
        # raise UserError('TESTAS')      
        return res


                

                