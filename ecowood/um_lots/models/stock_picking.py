import logging

from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id')

    # Elements transferred from sorting view from unsorted lamels to sorted lot
    unsorted_lot_id = fields.Many2one('stock.production.lot')
    average_price = fields.Monetary(help="average price of current id")
    transferred_square_meters = fields.Float(help="Square meters m^2 from unsorted lot")
    square_meters_price = fields.Float(compute="_compute_squared_meters_price")
    #############

    product_id = fields.Many2one('product.product', 'Product', related='move_lines.product_id', readonly=True,
                                 store=True)

    product_uom_qty = fields.Float(related='move_lines.product_uom_qty', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', related='move_lines.lot_id', readonly=True)
    thickness = fields.Float(related='lot_id.thickness', string='Storis (mm)')
    width = fields.Float(related='lot_id.width', string='Plotis (mm)')
    length1 = fields.Float(related='lot_id.length1', string='Ilgis (mm)')
    volume = fields.Float(related='lot_id.volume', string='Apimtis (m3)')
    type_of = fields.Char(related='lot_id.type_of', string='Rūšis')
    # calibration_spoilage = fields.Float(related='move_line_ids_without_package.calibration_spoilage', readonly=True)
    calibration_spoilage = fields.Float(compute='_compute_calibration_spoilage', store=False, readonly=True)

    # Timing
    start_time = fields.Datetime(string="Pradžios laikas")
    end_time = fields.Datetime(string="Sustojimo laikas")

    calibrating_lot = fields.Char(help="Lot that currently calibrating")




    @api.depends('transferred_square_meters', "average_price")
    def _compute_squared_meters_price(self):
        for record in self:
            record.square_meters_price = record.transferred_square_meters * record.average_price
            logging.info(f"{record.transferred_square_meters=} * {record.average_price} = {record.square_meters_price}")


    @api.depends('move_ids_without_package.calibration_spoilage')
    def _compute_calibration_spoilage(self):
        for record in self:
            record.calibration_spoilage = sum(record.mapped('move_ids_without_package.calibration_spoilage'))

    def process_calibration(self):
        for record in self:
            order_lines = []
            sp = self.env['stock.picking']
            # get product width and thickness after calibration
            for move_line in record.move_line_ids_without_package:
                move_id = move_line.move_id
                new_product_id = self.env.ref('um_lots.item_dried_boards_calibrated')
                print('test11')
                # Process old and new product
                primary_stock_quant, secondary_product_quant = move_line.ecowood_process_product(new_product_id=new_product_id.id)
                print('her123')
                print(primary_stock_quant)
                print(secondary_product_quant)

                width, thickness = record.width_thickness_calibration(width=move_id.lot_id.width,
                                                                      thickness=move_id.lot_id.thickness)
                # Set width and thickness of lot with new calculated values
                move_id.lot_id.width = width
                move_id.lot_id.thickness = thickness

                calibration_end_sp = self.env.ref('um_lots.operation_type_calibration_ending')

                spoilage = move_id.calibration_spoilage
                #Set spoilage on newly produced LOT
                secondary_product_quant.lot_id.calibration_spoilage += spoilage
                # New stock picking for removal of product from current location
                move_id.create_new_sp(picking_type_id=calibration_end_sp, product_id=new_product_id, spoilage=spoilage)

    def process_sorting(self):
        """
        Transfer from Nerušiuotos lamelės to rušiuotos lamelės
        """
        for record in self:
            order_lines = []
            sp = self.env['stock.picking']
            # get product width and thickness after calibration
            for move_line in record.move_line_ids_without_package:
                move_id = move_line.move_id
                new_product_id = self.env.ref('ecowood_sorting.item_sorted_lamels')
                # Process old and new product
                move_line.from_serial_to_serial(new_product_id=new_product_id.id)  # Overide

                calibration_end_sp = self.env.ref('ecowood_sorting.operation_type_sort_ending')

                # New stock picking for removal of product from current location
                move_id.create_new_sp(picking_type_id=calibration_end_sp, product_id=new_product_id)

    def _action_done(self):
        """
        When pick operation is done this action is triggered
        """
        res = super()._action_done()
        for record in self:
            operation_type_send_to_calibration = self.env.ref("um_lots.operation_type_send_to_calibration")
            operation_type_calibration = self.env.ref("um_lots.operation_type_calibration")

            # operation_type_sorting = self.env.ref("ecowood_sorting.operation_type_sorting")

            if self.picking_type_id.name == operation_type_send_to_calibration.name:
                # Create new stock picking 'Kalibravimas'
                record.move_ids_without_package.create_new_sp(picking_type_id=operation_type_calibration)
            # check if picking type 'Kalibravimas'
            if self.picking_type_id.name == operation_type_calibration.name:
                record.process_calibration()

        return res

    def width_thickness_calibration(self, width=False, thickness=False):
        # Standartinių pločių kalibravimas
        if width == 145 and thickness == 29:
            width = 125
            thickness = 24
        elif width == 170 and thickness == 29:
            width = 150
            thickness = 24
        elif width == 215 and thickness == 29:
            width = 150
            thickness = 24
        elif width == 270 and thickness == 29:
            width = 150
            thickness = 24
        # Nestandartinių pločių kalibravimas
        elif width == 85 and thickness == 29:
            width = 74
            thickness = 24
        elif width == 90 and thickness == 29:
            width = 74
            thickness = 24
        elif width == 95 and thickness == 29:
            width = 74
            thickness = 24
        elif width == 100 and thickness == 29:
            width = 74
            thickness = 24
        elif width == 105 and thickness == 29:
            width = 94
            thickness = 24
        elif width == 110 and thickness == 29:
            width = 94
            thickness = 24
        elif width == 115 and thickness == 29:
            width = 94
            thickness = 24
        elif width == 120 and thickness == 29:
            width = 94
            thickness = 24
        elif width == 125 and thickness == 29:
            width = 106
            thickness = 24
        elif width == 130 and thickness == 29:
            width = 106
            thickness = 24
        elif width == 135 and thickness == 29:
            width = 106
            thickness = 24
        elif width == 140 and thickness == 29:
            width = 125
            thickness = 24
        elif width == 150 and thickness == 29:
            width = 125
            thickness = 24
        elif width == 155 and thickness == 29:
            width = 125
            thickness = 24
        elif width == 160 and thickness == 29:
            width = 125
            thickness = 24
        elif width == 165 and thickness == 29:
            width = 150
            thickness = 24
        elif width == 175 and thickness == 29:
            width = 150
            thickness = 24
        elif width == 180 and thickness == 29:
            width = 160
            thickness = 24
        elif width == 185 and thickness == 29:
            width = 160
            thickness = 24
        elif width == 190 and thickness == 29:
            width = 160
            thickness = 24
        elif width == 195 and thickness == 29:
            width = 160
            thickness = 24
        elif width == 200 and thickness == 29:
            width = 180
            thickness = 24
        return width, thickness
