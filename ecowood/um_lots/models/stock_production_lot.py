import logging

from odoo import api, fields, models


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    thickness = fields.Float(string='Storis (mm)', tracking=True)
    width = fields.Float(string='Plotis (mm)', tracking=True)
    length1 = fields.Float(string='Ilgis (mm)', tracking=True)
    volume = fields.Float(string='Kiekis (m³)',
                          tracking=True,
                          digits=(12, 3),
                          compute="_compute_volume",
                          store=True,
                          )
    volume_price = fields.Float(string='m³ kaina',
                                tracking=True,
                                digits=(12, 3),
                                compute="_compute_volume_price",
                                store=True
                                )

    type_of = fields.Char(string="Rūšis", tracking=True)

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True)

    palette_price = fields.Monetary(tracking=True, store=True)  # implicitly depends on currency_id as currency_field
    palette_price_sorted = fields.Monetary(tracking=True, store=True, compute="_compute_quantity_m2_price")
    average_price = fields.Monetary(string='Vidutinė kvadrato kaina', tracking=True, compute="_compute_average_lot",
                                    help="Kvadrato kaina priklausanti nuo kiekio", readonly=True, store=True)

    count_stop = fields.Integer(help="Average is counted until this value", default=1000)
    is_sorted_and_unsorted = fields.Boolean(help="is this sorted product", compute="_is_sorted_and_unsorted")
    is_sorted = fields.Boolean(help="is this sorted product", compute="_is_sorted")
    is_unsorted = fields.Boolean(help="is this sorted product", compute="_is_unsorted")

    transferred_stock_move_ids = fields.One2many("stock.picking", compute="_transferred_stock_move_ids",
                                                 help="This field show transfers that belong to this "
                                                      "lot'stock.product.lot")

    import_qty = fields.Float(string='Importavimo kiekis')

    quantity_squared = fields.Float(help="Quantity squared", string="Kiekis (m²)", compute='_compute_volume_quantity')

    calibration_state = fields.Selection([('ready', 'Ready'), ('in_progress', 'In Progress'),
                                          ('done', 'Done'), ], string='Status',
                                         default='ready', readonly=True,
                                         help="calibration status")

    pock_number = fields.Integer(string="Poko numeris")
    delivery_date = fields.Text(string="Atvykimo data")
    supplier = fields.Text(string="Tiekėjas")
    account_number = fields.Text(string="Sąskaitos numeris")

    group = fields.Selection([('1', '1'), ('3', '3'),
                              ('4', '4'), ], string='Grupė',
                             default='1')
    calibration_spoilage = fields.Float(string='Brokas', readonly="1")

    @api.depends("thickness", "width", "length1", "product_qty")
    def _compute_volume(self):
        """
        volume field - computation
        """
        for record in self:
            thickness_m = record.thickness / 1000
            width_in_m = record.width / 1000
            length_in_m = record.length1 / 1000
            record.volume = thickness_m * width_in_m * length_in_m * record.product_qty

    @api.depends("palette_price", "palette_price_sorted", "volume")
    def _compute_volume_price(self):
        """
        volume_price field - computation
        """
        for record in self:
            if record.palette_price_sorted:
                record.volume_price = record.palette_price_sorted / record.volume if record.volume else 0
            if record.palette_price:
                record.volume_price = record.palette_price / record.volume if record.volume else 0

    # @api.depends("volume", "volume_price")
    # def _compute_palette_price(self):
    #     """
    #     pallete_price  variable computation
    #     """
    #     for record in self:
    #         record.palette_price = record.volume_price * record.volume

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if 'import_qty' in vals:
            if vals['import_qty'] > 0:
                stock_quant = self.env['stock.quant'].create({
                    'product_id': res.product_id.id,
                    'lot_id': res.id,
                    'location_id': self.env.ref('um_lots.work_location_warehouse').id,
                    'quantity': vals['import_qty'],
                })
        return res

    def _is_sorted(self):
        lamels = self.env.ref('ecowood_sorting.item_sorted_lamels_product_template')
        if self.product_id.id == lamels.id:
            self.is_sorted = True
            return True
        else:
            self.is_sorted = False
            return False

    def _is_unsorted(self):
        unsorted_lamels = self.env.ref('ecowood_sorting.item_unsorted_lamels_product_template')
        if self.product_id.id == unsorted_lamels.id:
            self.is_unsorted = True
            return True
        else:
            self.is_unsorted = False
            return False

    def _is_sorted_and_unsorted(self):
        if self._is_sorted() or self._is_unsorted():
            self.is_sorted_and_unsorted = True
        else:
            self.is_sorted_and_unsorted = False

    def _transferred_stock_move_ids(self):
        lamels_sorted = self.env.ref('ecowood_sorting.item_sorted_lamels')
        lamels_unsorted = self.env.ref('ecowood_sorting.item_unsorted_lamels')
        warehouse_end = self.env.ref('ecowood_sorting.operation_type_sort_ending')  # Rušiavimo užbaigimas/PAB
        origin_id = self.id

        if self.product_id == lamels_sorted or self.product_id == lamels_unsorted:

            # Sorting palette stores as much ID as 1000, if it's overflowed removes the oldest elements
            if self.product_id.id == lamels_sorted.id:
                stock_picking__search = self.env['stock.picking'].search(
                    [('picking_type_id', '=', warehouse_end.id), ('lot_id', '=', origin_id)], order="id desc")

                total_quantity = 0
                picked_pickings = self.env['stock.picking']
                for transfer in stock_picking__search:
                    if total_quantity <= self.count_stop and total_quantity + transfer.product_uom_qty <= self.count_stop:
                        total_quantity += transfer.product_uom_qty
                        picked_pickings += transfer

                self.transferred_stock_move_ids = picked_pickings.sorted(key="date")
                return
            # For unsorted lamels, get all transfers
            if self.product_id.id == lamels_unsorted.id:
                stock_picking__search = self.env['stock.picking'].search(
                    [('picking_type_id', '=', warehouse_end.id), ('unsorted_lot_id', '=', origin_id)], order="id asc")
                self.transferred_stock_move_ids = stock_picking__search

        # Fix error when opening calibration
        self.transferred_stock_move_ids = self.env['stock.picking']
        return

    def _get_company_currency(self):
        for partner in self:
            partner.currency_id = partner.sudo().company_id.currency_id

    @api.depends("count_stop", "product_qty")
    def _compute_quantity_m2_price(self):
        if len(self) == 1:
            origin_id = self.id
            warehouse_end = self.env.ref('ecowood_sorting.operation_type_sort_ending')  # Rušiavimo užbaigimas/PAB
            stock_picking__search = self.env['stock.picking'].search(
                [('picking_type_id', '=', warehouse_end.id), ('lot_id', '=', origin_id)], order="id desc")
            total_value = sum(stock_picking__search.mapped("square_meters_price"))
            self.palette_price_sorted = total_value

    @api.depends("count_stop", "product_qty")
    def _compute_average(self):
        """
        Compute average price based
        :return:
        """
        if len(self) == 1:
            warehouse_end = self.env.ref('ecowood_sorting.operation_type_sort_ending')  # Rušiavimo užbaigimas/PAB
            logging.info(f"stock.production.lot self: {self} {self.display_name}")
            origin_id = self.id
            stock_picking__search = self.env['stock.picking'].search(
                [('picking_type_id', '=', warehouse_end.id), ('lot_id', '=', origin_id)], order="id desc")
            logging.info(f"stock_picking__search: {stock_picking__search} {len(stock_picking__search)}")
            logging.info(f"{[x.unsorted_lot_id.name for x in stock_picking__search]}")
            if stock_picking__search:

                total_counted = 0
                average_price = []
                counted_pickings = []
                counted_quantity = []
                logging.info(f'stock_picking__search quantities: {stock_picking__search.mapped("product_uom_qty")}')
                for picking in stock_picking__search:
                    unsorted_pallet_sent_qty = picking.product_uom_qty
                    if total_counted < self.count_stop:
                        total_counted += unsorted_pallet_sent_qty
                        counted_quantity.append(unsorted_pallet_sent_qty)

                        sorting_model_origin = self.env['sorting.model'].search(
                            [('serial_number', '=', picking.unsorted_lot_id.name)], limit=1)
                        if not sorting_model_origin:  # If record is not found search if it's archived
                            sorting_model_origin = self.env['sorting.model'].search(
                                [('serial_number', '=', picking.unsorted_lot_id.name), ('active', '=', False)],
                                limit=1)

                        fixed_average = sorting_model_origin.fixed_average_price  # Get average price
                        lot_price = unsorted_pallet_sent_qty * fixed_average
                        logging.info(
                            f"{sorting_model_origin.serial_number=} {sorting_model_origin.fixed_average_price=}")
                        logging.info(f"lotprice = {unsorted_pallet_sent_qty} * {fixed_average} = {lot_price} ")
                        average_price.append(lot_price)
                        counted_pickings.append(picking)
                    else:
                        self.average_price = sum(average_price) / sum(counted_quantity) if sum(counted_quantity) else 0
                        logging.info(
                            F"Average price: {sum(average_price)} / {sum(counted_quantity)} = {self.average_price}")
                        logging.info(f"Reached stop: '{self.count_stop}' Current added quantities: `{total_counted}`")
                        logging.info(f"Average price: {self.average_price} of {self} selected: {counted_pickings}")
                        return
                self.average_price = sum(average_price) / sum(counted_quantity) if sum(counted_quantity) else 0

    @api.depends("palette_price", "quantity_squared")
    def _compute_average_lot(self):
        """
        Compute average price when importing price
        :return:
        """
        for rec in self:
            if rec.palette_price:
                rec.average_price = rec.palette_price / rec.quantity_squared if rec.quantity_squared else 0
            if rec.palette_price_sorted:
                rec.average_price = rec.palette_price_sorted / rec.quantity_squared if rec.quantity_squared else 0

    def calculate_average(self, price, quantity):
        try:
            average_price = price / quantity
            return average_price
        except ZeroDivisionError:
            logging.warning("Decision by zero error")
            self.average_price = 0

    @api.depends('width', 'length1', 'product_qty')
    def _compute_volume_quantity(self):
        """
        Compute squared  from product lot values
        """
        for record in self:
            # record.volume = 0
            width_in_m = record.width / 1000
            length_in_m = record.length1 / 1000
            volume = width_in_m * length_in_m * record.product_qty
            logging.info(f"{width_in_m=} * {length_in_m=} * {record.product_qty=} = {volume=}")
            record.quantity_squared = volume
