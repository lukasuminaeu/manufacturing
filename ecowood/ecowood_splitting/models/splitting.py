# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from enum import Enum
_logger = logging.getLogger(__name__)

class SplittingModel(models.Model):
    _name = 'splitting.model'
    _description = 'Splitting module interface'

    name = fields.Char()
    value = fields.Integer()
    description = fields.Text()
    options = fields.Selection([('x4','x4 (4,5 mm)'), ('x5', 'x5 (3,8 mm)'), ('x6', "x6 (2.5 mm)")], 
            string = "Skaldymas")
            # required=True)
    _inherit = [ 'barcodes.barcode_events_mixin']
    type_of = fields.Char(string="Rūšis")
    serial_number = fields.Char(string="Partijos nr")
    product = fields.Many2one("product.template")
    start_time = fields.Datetime(string="Pradžios laikas", help="Time counted from first time code is scanned")
    end_time = fields.Datetime(string="Pabaigos laikas")
    created_on = fields.Datetime(help="Serial number create time.",string= "Sukūrimo laikas")

    length1 = fields.Float(string="Ilgis (mm)")
    width = fields.Float(string="Plotis (mm)")
    size = fields.Float(string="Storis (mm)")
    quantity = fields.Float(string="Kiekis")
    square_meters = fields.Char(string="m²")

    effective_hours = fields.Float("Visa Darbo Trukmė", compute='_compute_effective_hours', compute_sudo=True,
                                   store=True, help="Time spent on this task.")

    state = fields.Selection([('ready', 'Ready'), ('in_progress', 'In Progress'),
                              ('done', 'Done'), ], string='Status',
                             default='ready', readonly=True,
                             help="when state is set to Done, this entry can't be opened by caning barcode")
    active = fields.Boolean(string="Active", default=True)

    def list_barcode_scanned(self, barcode):
        logging.info(f"Calling from list view {barcode}")
        return self.env["stock.picking"].process_splitting_barcode(barcode)
    
    def action_transfer_calibrated(self,lots):
        """
        Transfer From
        Source Location	WH/Stock/Skaldymas/IN
        Destination Location	WH/Stock/Skaldymas/OUT
        :return:
        """ 
        for lot in lots:
            calibrated_boards= self.env.ref("um_lots.item_dried_boards_calibrated_product_template")
            picking_type_splitting_in_out = self.env.ref("ecowood_splitting.operation_type_splitting")
            lot_id = self.env['stock.production.lot'].search([('name', '=', lot.serial_number),('product_id','=',calibrated_boards.id)])
            #gets values from options code
            option_string=lot.options
            option_value = 0
            new_width = 0
            if not option_string:
                option_value = 1
                new_width = 1
            elif option_string == "x4":
                option_value = 4
                new_width = 4.5
            elif option_string == "x5":
                option_value = 5
                new_width = 3.8
            elif option_string == "x6":
                option_value = 6
                new_width = 2.5
            lamels_unsorted = self.env.ref("ecowood_sorting.item_unsorted_lamels_product_template")
            print(
                f"operation type: {picking_type_splitting_in_out} / {picking_type_splitting_in_out.name}\nold product:{lamels_unsorted} "
                f"new product:{lamels_unsorted} / {lamels_unsorted.name} ")
            quantity= lot_id.product_qty
            #complete splitting(from IN to OUT)
            stock_picking = self.create_transfer(picking_type_id=picking_type_splitting_in_out, product_id=calibrated_boards,
                                lot=lot_id)
            #write off calibrated boards, transfer to sorting
            self.transfer_lot(lot_id,stock_picking,quantity,option_value)
            lot.state="done"
            lot.active=False
            lot.end_time = fields.Datetime.now()
            split_lot = self.env['splitting.model'].search([('serial_number', '=', lot.name)])
            form_value = {
                            'product': lamels_unsorted.id,
                            'serial_number': lot.serial_number,
                            'created_on': lot.create_date,
                            'length1': lot_id.length1,
                            'width': lot_id.width,
                            'size': new_width,
                            'quantity': quantity*option_value,
                            'type_of': lot_id.type_of
                        }
            lot_id.thickness=new_width
            self.env['sorting.model'].create(form_value)

            lot_id.average_price/=option_value
            logging.info(f"Action done. lot passed to sorting module")
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def create_transfer(self, lot, picking_type_id=False, product_id=False):
        """ Creates stock.picking Transfer
            Operation Type: Skaldymas
            Source Location 	Skaldymas IN
            Destination Location: 	Skaldymas OUT
        :return transfer quantity
        """
        order_lines = []
        order_lines.append(
            (0, 0,
                {
                    'product_id': product_id.id, 
                    'lot_id': lot.id,
                    'product_uom': product_id.uom_id.id,
                    'company_id': self.env.user.company_id.id,
                    'name': product_id and product_id.name or self.product_id.name,
                    'location_id': picking_type_id.default_location_src_id.id,  
                    'location_dest_id': picking_type_id.default_location_dest_id.id,  
                    'product_uom_qty': lot.product_qty,
                }
                ))
        picking_id = self.env['stock.picking'].create({
            'picking_type_id': picking_type_id.id,
            'location_id': picking_type_id.default_location_src_id.id,
            'location_dest_id': picking_type_id.default_location_dest_id.id,
            'move_lines': order_lines,
            'move_type': 'direct',
        })
        logging.info(f"Record created: {picking_id}")
        logging.info("\n"
                        f"Operation Type:       {picking_type_id.name}\n"
                        f"Product:              {product_id.name}\n"
                        f"Source Location:      {picking_type_id.default_location_src_id.name}\n"
                        f"Destination Location: {picking_type_id.default_location_dest_id.name}\n"
                        f"Order lines:          {order_lines}\n")
        picking_id.action_confirm()
        # Click 'Availability' button
        picking_id.action_assign()
        # Click 'Validate' button '_action_done' is triggered in 'stock.picking'
        picking_id.button_validate()
        return picking_id

    def transfer_lot(self, lot, stock_picking,quantity, multiplier):
        lamels_unsorted = self.env.ref('ecowood_sorting.item_unsorted_lamels')
        picking_type_split_end = self.env.ref("ecowood_splitting.operation_type_split_ending")
        secondary_product_quant = self.env['stock.quant'].search([
            ('product_id', '=', lamels_unsorted.id),
            ('location_id', '=', picking_type_split_end.default_location_src_id.id),  #
            ('lot_id', '=', lot.id),
        ], limit=1)
        lamels_unsorted = self.env.ref('ecowood_sorting.item_unsorted_lamels')
        if secondary_product_quant:
            secondary_product = self.env['product.product'].browse([lot.product_id.id])
            secondary_stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', lamels_unsorted.id),
                    ('location_id', '=', picking_type_split_end.default_location_src_id.id),
                ], limit=1)
            secondary_product_quant.update({
                'quantity': quantity*multiplier +secondary_stock_quant
            })
        else:
            #creates new product quant so it could be used for transfer
            secondary_product_quant = self.env['stock.quant'].create({
                'product_id': lamels_unsorted.id,
                'location_id': picking_type_split_end.default_location_src_id.id,
                'lot_id': lot.id,
                'quantity': quantity*multiplier
            })
        primary_stock_quant = self.env['stock.quant'].search([
            ('product_id', '=', stock_picking.product_id.id),
            ('location_id', '=', stock_picking.location_dest_id.id),
            ('lot_id', '=', stock_picking.lot_id.id),
        ], limit=1)
        #unlinks original quant
        if primary_stock_quant:
            logging.info(f"Removing {primary_stock_quant}")
            logging.info(f"reached unlink 1, going to end transfer {primary_stock_quant.lot_id}  {primary_stock_quant.product_id}  {primary_stock_quant.reserved_quantity}  {primary_stock_quant.available_quantity}   {primary_stock_quant.quantity}")
            primary_stock_quant.sudo().unlink()
        self.create_end_transfer(lot = lot, quant_out = secondary_product_quant, quantity = quantity, multiplier = multiplier)
    
    def create_end_transfer(self, lot, quant_out,quantity, multiplier):
        picking_type_split_end = self.env.ref("ecowood_splitting.operation_type_split_ending")
        lamels_unsorted = self.env.ref('ecowood_sorting.item_unsorted_lamels')
        lot_id = self.env['stock.production.lot'].browse([lot.id])
        self.env.cr.execute(f"UPDATE stock_production_lot set product_id={lamels_unsorted.id} WHERE id={lot_id.id}")
        order_lines = [(0, 0,
            {
                'product_id': lamels_unsorted.id, 
                'lot_id': lot.id,
                'product_uom': lamels_unsorted.uom_id.id,
                'company_id': self.env.user.company_id.id,
                'name': lamels_unsorted and lamels_unsorted.name or self.product_id.name,
                'location_id': picking_type_split_end.default_location_src_id.id,  
                'location_dest_id': picking_type_split_end.default_location_dest_id.id,  
                'product_uom_qty': quantity*multiplier,
            }
            )]
        picking_id = self.env['stock.picking'].create({
            'picking_type_id': picking_type_split_end.id,
            'location_id': picking_type_split_end.default_location_src_id.id,
            'location_dest_id': picking_type_split_end.default_location_dest_id.id,
            'move_lines': order_lines,
            'move_type': 'direct',
            })
        picking_id.action_confirm()
        # # Click 'Availability' button
        picking_id.action_assign()
        # # Click 'Validate' button
        picking_id.button_validate()
        if quant_out:
            logging.info(f"Deleting '{quant_out}' {quant_out.display_name}' record")
            quant_out.sudo().unlink()
        logging.info(f"Transfer completed, quants deleted. Added quantity {quantity*multiplier} to lot id {lot.id} of unsorted lamels")
        transfer_to_lot = self.env['stock.production.lot'].search([('name', '=', lot.name)],limit=1)
        transfer_to_lot.message_post(
            body=f"Added quantity: {quantity} From: '{lot.name}'")