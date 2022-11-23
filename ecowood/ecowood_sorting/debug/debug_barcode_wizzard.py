# -*- coding: utf-8 -*-

from odoo import models, fields


class DebugBarcode(models.TransientModel):
    """
    Debug Wizards to popup for barcode entry
    """
    _name = "debug.barcode.wizard"
    _description = "Debug wizard used to call entries from sorting.model"
    name = fields.Char(help="Debug barcode entry", default="IN00002")

    def debug_call_barcode(self):
        stock_picking = self.env['stock.picking'].browse()
        return stock_picking.process_barcode(self.name)

    def debug_create_calibration_item(self):
        stock_picking = self.env['stock.picking'].browse()

        unsorted_lot_display_name = "DRY-1"
        unsorted_pallet_price = 1000
        unsorted_thickness = 1
        unsorted_width = 2
        unsorted_length = 3
        unsorted_type = "01TYPE"

        product = self.env.ref('um_lots.item_dried_boards_product_template')
        stock_location = self.env.ref("um_lots.work_location_warehouse")

        find_lot = self.env['stock.production.lot'].search([
            ('name', '=like', 'DRY%'),
        ], order="id desc")
        if find_lot:
            last_lot = find_lot[0]
            name, number = find_lot[0].display_name.split("-")

            # increment lot
            lot1_unsorted = self.env['stock.production.lot'].create({
                'name': f"{name}-{int(number) + 1}",
                'product_id': product.id,
                'company_id': self.env.company.id,
                'palette_price': unsorted_pallet_price,
                'thickness': unsorted_thickness,
                'width': unsorted_width,
                'length1': unsorted_length,
                'type_of': unsorted_type,
            })
        else:
            # create unique lot
            lot1_unsorted = self.env['stock.production.lot'].create({
                'name': f"{unsorted_lot_display_name}",
                'product_id': product.id,
                'company_id': self.env.company.id,
                'palette_price': unsorted_pallet_price,
                'thickness': unsorted_thickness,
                'width': unsorted_width,
                'length1': unsorted_length,
                'type_of': unsorted_type,
            })
        inventory_quant = self.env['stock.quant'].create({
            'location_id': stock_location.id,
            'product_id': product.id,
            'lot_id': lot1_unsorted.id,
            'inventory_quantity': 1000
        })
        inventory_quant.action_apply_inventory()
