from odoo import models, fields, _, api
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def create_picking_pallet_scrap(self, new_package_id):
        picking_type_id_pallet_scrap = self.env.ref('um_stock_barcode.operation_type_pallet_scrap')
        #Find open pallet scrap stock.picking for today. If there isnt any, create new one 
        picking_id_pallet_scrap = self.env['stock.picking'].search([
            ('picking_type_id', '=', picking_type_id_pallet_scrap.id),
            ('state', 'not in', ('cancel', 'done')),
            ('create_date', '>=', datetime.now().replace(hour=00,minute=0,second=0,microsecond=0)),
            ('create_date', '<', datetime.now().replace(hour=00,minute=0,second=0,microsecond=0) + timedelta(days=1)),
        ])
        if picking_id_pallet_scrap:
            picking_id_pallet_scrap.move_ids_without_package.filtered(
                lambda x: x.product_id.id == self.env.ref('um_stock_barcode.product_pallet').id
            ).product_uom_qty += 1
            
            picking_id_pallet_scrap.action_assign()
        else:
            picking_id_pallet_scrap = self.env['stock.picking'].create({
                'picking_type_id': picking_type_id_pallet_scrap.id,
                'location_id': self.env.ref('um_mrp_data.stock_location_sandelis').id,
                'location_dest_id': self.env.ref('um_stock_barcode.stock_location_pallet_scrap').id,
            })
            move_ids_without_package = self.env['stock.move'].create({
                'product_id': self.env.ref('um_stock_barcode.product_pallet').id,
                'product_uom': self.env.ref('um_stock_barcode.product_pallet').uom_id.id,
                'product_uom_qty': 1,
                'name': picking_id_pallet_scrap.name,
                'location_id': self.env.ref('um_mrp_data.stock_location_sandelis').id,
                'location_dest_id': self.env.ref('um_stock_barcode.stock_location_pallet_scrap').id,
            })
            picking_id_pallet_scrap.move_ids_without_package += move_ids_without_package

            picking_id_pallet_scrap.action_confirm()
            picking_id_pallet_scrap.action_assign()

        new_package_id.picking_id_pallet_scrap = picking_id_pallet_scrap.id
        picking_id_pallet_scrap.select_packages_ids += picking_id_pallet_scrap.select_packages_ids.create({
            'package_id': new_package_id.id
        })

    def action_put_in_pack(self):
        res = super().action_put_in_pack()
        
        self.create_picking_pallet_scrap(res)
        
        return res
