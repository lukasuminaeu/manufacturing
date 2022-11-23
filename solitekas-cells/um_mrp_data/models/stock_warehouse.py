# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, _lt, api, fields, models

class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _get_input_output_locations(self, reception_steps, delivery_steps):
        #Made here standard location for stock.picking.type to be 'Sandelis'
        #because on module update, it updates source location from here.
        location_sandelis = self.env.ref('um_mrp_data.stock_location_sandelis')
        return (location_sandelis if reception_steps == 'one_step' else self.wh_input_stock_loc_id,
                location_sandelis if delivery_steps == 'ship_only' else self.wh_output_stock_loc_id)

    def _get_picking_type_create_values(self, max_sequence):
        res = super()._get_picking_type_create_values(max_sequence)
        # #Umina (Valentas) edit: make standard location for internal transfer as 'Gamyba', because it is needed
        # #in barcodes module to be able to chooose child locations when making internal transfer through barcode module.
        res[0]['int_type_id']['default_location_src_id'] = self.env.ref('um_mrp_data.stock_location_partner_production_gamyba').id
        res[0]['int_type_id']['default_location_dest_id'] = self.env.ref('um_mrp_data.stock_location_partner_production_gamyba').id

        return res

