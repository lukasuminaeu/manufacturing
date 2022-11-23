# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api
from odoo.addons.ecowood_sorting.sorting.helper_methods import display_popup_message
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

from enum import Enum


class SortingModel(models.Model):
    _name = "sorting.model"
    _description = "Sorting lamels interface with work hours/work operations"
    _inherit = ['timer.mixin', 'barcodes.barcode_events_mixin']
    _rec_name = "complete_name"

    complete_name = fields.Char("Full Name", compute='_compute_complete_name', store=True)
    serial_number = fields.Char()
    product = fields.Many2one("product.template")
    created_on = fields.Datetime(help="Serial number create time.")
    start_time = fields.Datetime(string="Pradžios laikas", help="Time counted from first time form is created")
    stop_time = fields.Datetime(string="Stabdymo laikas")
    end_time = fields.Datetime(string="Pabaigos laikas")

    length1 = fields.Float(string="Ilgis (mm)")
    width = fields.Float(string="Plotis (mm)")
    size = fields.Float(string="Storis (mm)")
    quantity = fields.Float(string="Kiekis")
    square_meters = fields.Float(string="m²", compute="_compute_squared_meters", store=True)

    type_of = fields.Char(string="Rūšis")

    sorted_lamels = fields.Float(string="Bendras išrušiuotų  lamelių kiekis", compute="_calculate_total", store=True)

    palette_ids = fields.One2many(comodel_name='sorting.saved.operations', inverse_name="palette_history_id")
    work_time_ids = fields.One2many(comodel_name="sorting.saved.time", inverse_name="work_time_id")

    effective_hours = fields.Float("Visa Darbo Trukmė", compute='_compute_effective_hours', compute_sudo=True,
                                   store=True, help="Time spent on this task.")

    state = fields.Selection([('ready', 'Ready'), ('in_progress', 'In Progress'),
                              ('done', 'Done'), ], string='Status',
                             default='ready', readonly=True,
                             help="when state is set to Done, this entry can't be opened by caning barcode")

    active = fields.Boolean(string="Active", default=True)

    transfer_qty = fields.Float(help="Quantity being transferred from 'Nerūriuotos lameles' to 'Lamelės'")

    # Monetary fields
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id')

    fixed_total_price = fields.Monetary(help="Total unsorted lammel price")

    fixed_average_price = fields.Monetary(help="Average square meter price")

    @api.depends("serial_number")
    def _compute_complete_name(self):
        for rec in self:
            formatted_date = rec.create_date.strftime("%Y/%m/%d - %H:%M:%S")
            rec.complete_name = f"{rec.serial_number} - {formatted_date}"

    @api.depends("palette_ids.quantity")
    def _calculate_total(self):
        "Get total sum of completed units "
        self.sorted_lamels = sum(self.palette_ids.mapped("quantity"))

    @api.depends("work_time_ids.work_time")
    def _compute_effective_hours(self):
        for task in self:
            task.effective_hours = round(sum(self.work_time_ids.mapped('work_time')), 2)

    def form_barcode_scanned(self, barcode):
        """
        This method is used inside sorting model form
        :param barcode: scanned barcode
        """
        print(f"Calling from form sorting.model  {barcode}")
        return self.process_scanned_barcode(barcode)

    def list_barcode_scanned(self, barcode):
        """
        This method is used inside sorting model view
        :param barcode: scanned barcode
        """
        print(f"Calling from list view {barcode}")
        return self.env["stock.picking"].process_barcode(barcode)

    def process_scanned_barcode(self, barcode):
        """
            Prints barcode fetched from current model
            :param barcode: barcode from list view
            :return:

        """

        class ExtendedEnum(Enum):

            @classmethod
            def list(cls):
                return list(map(lambda c: c.value, cls))

        class OperationType(ExtendedEnum):
            CONFIRM_MOVE = "PATVIRTINTI PADEJIMA"
            STOP = 'SUSTABDYTI'
            CLOSE = 'UZDARYTI'
            ADD_SORTING = 'PRIDĖTI'

        if barcode == OperationType.ADD_SORTING.value:
            return
        if barcode == OperationType.CONFIRM_MOVE.value:
            ready_palettes = self.palette_ids.filtered(lambda rec: rec.state in "ready")
            if not ready_palettes:
                message = "No ready palettes to move"
                logging.warning(message)
                return display_popup_message(f"Warning", message, display_type="warning")

            action = self.env.ref("ecowood_sorting.wizard_confirm_action")
            confirm_prompt = action.sudo().read()[0]
            confirm_prompt['context'] = {'default_source_document': self.id}
            return confirm_prompt

        if barcode == OperationType.STOP.value:
            return self.stop_timer()
        if barcode == OperationType.CLOSE.value:
            return self.end_timer()

        if barcode.startswith("add"):
            return

        # 4.3 sorting from 'Nerušiuotos lamelės' to "Lamelės"
        lamels = self.env.ref("ecowood_sorting.item_sorted_lamels_product_template")
        lamel_sort_barcode_ids = self.env['stock.production.lot'].search([("product_id", "=", lamels.id)])
        lamel_sort_barcode_names = lamel_sort_barcode_ids.mapped("name")

        if barcode in lamel_sort_barcode_names:
            # First time scanned empty wizard sheet
            lot = self.env['stock.production.lot'].search([
                ('name', '=', barcode),
                ('product_id', '=', lamels.id),
            ], limit=1)

            created = self.env['sorting.popup.model'].create(
                {'type': f"{lot.type_of if lot.type_of else ''}",
                 'size': f"{lot.thickness}",
                 'width': f"{lot.width}",
                 'length1': f"{lot.length1}",
                 'quantity': "",
                 'current_model': self.id,
                 'serial': barcode
                 })

            return {
                "type": "ir.actions.act_window",
                "res_model": "sorting.popup.model",
                "views": [[False, "form"]],
                "res_id": created.id,
                "target": "new",
            }

    def init_timer(self):
        """
        Start counting timer from the first time form is created in database
        """
        if not self.start_time:
            self.action_timer_start()
            self.start_time = fields.Datetime.now()

    def continue_timer(self):
        self.action_timer_resume()

    def stop_timer(self):
        """
        Stops timer and adds end date in work history
        """
        self.action_timer_pause()
        minutes_spent = self.user_timer_id._get_minutes_spent()
        converted_minutes_spent = minutes_spent * 60 / 3600
        print(f"Minutes spent: {minutes_spent} c: {converted_minutes_spent}")
        work_time_entry = self.work_time_ids.filtered(lambda rec: not rec.work_ended)
        if work_time_entry and not work_time_entry.work_ended:
            now = fields.Datetime.now()
            work_time_entry.work_ended = now
            self.stop_time = now

            work_duration = work_time_entry.work_ended - work_time_entry.work_started
            work_time_entry.work_time = work_duration.total_seconds() * 60 / 3600
            work_time_entry.worker = self._context.get("uid")
        return self.return_to_lamels_menu()

    def return_to_lamels_menu(self):
        action = self.env.ref("ecowood_sorting.sorting_model_action")
        main_view = action.sudo().read()[0]
        # clear the breadcrumb
        main_view['target'] = 'main'
        return main_view

    def end_timer(self):
        """
        Stops timer and adds end date in work history
        """
        is_debug = self.user_has_groups('ecowood_sorting.group_dev')
        sorted_elements = self.palette_ids.filtered(lambda r: r.state == "done")
        self.quantity = sum(sorted_elements.mapped("quantity"))
        self.square_meters = sum(sorted_elements.mapped("square_meters"))
        if is_debug:
            # Debug mode prevents card to be closed, only in development
            logging.info("-----------------------------")
            logging.info("DEBUG MODE")
            logging.info("-----------------------------")
            self.recalculate_average_price()
            return
        else:
            self.recalculate_average_price()
            time_duration = self.action_timer_stop()
            print(f"Loging work time: {time_duration}")
            work_time_entry = self.work_time_ids.filtered(lambda rec: not rec.work_ended)
            if not work_time_entry.work_ended:
                now = fields.Datetime.now()
                work_time_entry.work_ended = now
                self.end_time = now
                work_time_entry.work_time = time_duration
                self.state = "done"
                self.active = False
                logging.info(f"Setting {self} state to done")
        return self.return_to_lamels_menu()

    def recalculate_average_price(self):
        """Recalculate average price
        Lots/Serial Numbers 001 / Nerušiuotos lamelės
        Vieteto kanaina = Koks yra isrušiuotu lameliu kiekis / bendro kiekvio
        """
        try:
            self.fixed_average_price = self.fixed_total_price / self.square_meters
            logging.info(
                f"fixed_average_price = {self.fixed_total_price=} / {self.sorted_lamels=} = {self.fixed_average_price}")
        except ZeroDivisionError:
            self.fixed_average_price = 0
        warehouse_end = self.env.ref('ecowood_sorting.operation_type_sort_ending')  # Rušiavimo užbaigimas/PAB
        lamels_unsorted_ref = self.env.ref('ecowood_sorting.item_unsorted_lamels')

        unsorted_lot = self.env['stock.production.lot'].search(
            [('name', '=', self.serial_number), ('product_id', '=', lamels_unsorted_ref.id)], limit=1)

        stock_picking__search = self.env['stock.picking'].search(
            [('picking_type_id', '=', warehouse_end.id), ('unsorted_lot_id', '=', unsorted_lot.id)], order="id desc")
        print("Updating average price")
        print([x.average_price for x in stock_picking__search])

        for price in stock_picking__search:
            price.average_price = self.fixed_average_price
        print("To")
        print([x.average_price for x in stock_picking__search])

        # The new unit price is recalculated and sent back to the "Unsorted pallet" card
        unsorted_lot.message_post(body=f"Uždaryta paletė: {self.display_name}")
        unsorted_lot.average_price = self.fixed_average_price
        logging.info(f"Setting {unsorted_lot.display_name=} {unsorted_lot.average_price=}")

        # Recalculate prices for "Sorted lots"
        mapped_lot_id = stock_picking__search.mapped("lot_id")  # Filter only unique lot values
        for lot in mapped_lot_id:
            logging.info(f"Computing lot for {lot.display_name}")
            lot.count_stop = 1001
            lot.count_stop = 1000
            lot._compute_average()

    @api.depends("length1", "width", "quantity")
    def _compute_squared_meters(self):
        for record in self:
            # record.volume = 0
            width_in_m = record.width / 1000
            length_in_m = record.length1 / 1000
            squared_meters = width_in_m * length_in_m * record.quantity
            logging.info(f"{width_in_m=} * {length_in_m=} * {record.quantity=} = {squared_meters=}")
            record.square_meters = squared_meters



    def from_serial_to_serial(self, old_serial, new_serials, record, unsorted_pallet_lot):
        """
        This method transfers from one barcode certain quantity to another barcode
        """
        if not self.transfer_qty:
            raise UserError("No Quantity to transfer")

        # Product: Lameles
        for serial in new_serials:
            print(f"serial: {serial.serial_to} quantity:{serial.quantity}")
            transfer_to_serial = self.env['stock.production.lot'].search([('name', '=', serial.serial_to)], limit=1)
            secondary_product_quant = self.env['stock.quant'].search([
                ('product_id', '=', transfer_to_serial.product_id.id),
                ('location_id', '=', record.location_dest_id.id),  #
                ('lot_id', '=', transfer_to_serial.id),
            ], limit=1)
            if secondary_product_quant:
                secondary_product = self.env['product.product'].browse([transfer_to_serial.product_id.id])  # Lamelės
                secondary_stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', secondary_product.id),
                    ('location_id', '=', record.location_dest_id.id),
                ], limit=1)
                secondary_product_quant.update({
                    'quantity': secondary_stock_quant.quantity + serial.quantity
                })
            else:
                secondary_product_quant = self.env['stock.quant'].create({
                    'product_id': transfer_to_serial.product_id.id,
                    'location_id': record.location_dest_id.id,
                    'lot_id': transfer_to_serial.id,
                    'quantity': serial.quantity
                })

            # Remove 'WH/Stock/Rušiavimas/OUT'
            primary_stock_quant = self.env['stock.quant'].search([
                ('product_id', '=', record.product_id.id),
                ('location_id', '=', record.location_dest_id.id),
                ('lot_id', '=', record.lot_id.id),
            ], limit=1)

            if primary_stock_quant:
                logging.info(f"Removing {primary_stock_quant}")
                primary_stock_quant.sudo().unlink()

            logging.info(f"END transfer")
            # Transfer sorted lamels to WAREHOUSE
            self.create_end_transfer(lot=transfer_to_serial, new_serial=serial, quant_out=secondary_product_quant,
                                     unsorted_pallet_lot=unsorted_pallet_lot)

    def create_end_transfer(self, lot, new_serial, quant_out, unsorted_pallet_lot):
        """ Creates stock.picking Transfer
        WH/PAB/0000N
        Operation Type	Ecowood: Rušiavimo užbaigimas
        Source Location Lameles	WH/Stock/Rušiavimas/OUT
        Destination Location	WH/Stock/Sandėlys
        """
        picking_type_sorting_end = self.env.ref("ecowood_sorting.operation_type_sort_ending")
        lamels_sorted = self.env.ref('ecowood_sorting.item_sorted_lamels')
        picking_type_id = picking_type_sorting_end
        product_id = lamels_sorted
        for record in self:
            serial_quantity = new_serial.quantity
            order_lines = [(0, 0,
                            {
                                'product_id': product_id.id,  # Lameles
                                'lot_id': lot.id,
                                'product_uom': product_id.uom_id.id,
                                'company_id': record.env.user.company_id.id,
                                'name': product_id and product_id.name or record.product_id.name,
                                'location_id': picking_type_id.default_location_src_id.id,  # Rušiavimas OUT
                                'location_dest_id': picking_type_id.default_location_dest_id.id,  # Sandelys
                                'product_uom_qty': serial_quantity,
                            }
                            )]

            picking_id = record.env['stock.picking'].create({
                'picking_type_id': picking_type_id.id,
                'unsorted_lot_id': unsorted_pallet_lot.id,  # Original lot id
                'average_price': record.fixed_average_price,  # fixed price from sorting.model
                'transferred_square_meters': new_serial.square_meters,  # fixed price from sorting.model
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
                         f"Destination Location: {picking_type_id.default_location_dest_id.name}\n")

            picking_id.action_confirm()

            # Click 'Availability' button
            picking_id.action_assign()

            # Click 'Validate' button
            picking_id.button_validate()

            if quant_out:
                logging.info(f"Deleting '{quant_out}' {quant_out.display_name}' record")
                quant_out.sudo().unlink()

            transfer_to_lot = self.env['stock.production.lot'].search([('name', '=', new_serial.serial_to)],
                                                                      limit=1)  # TODO: possible to refactor up
            transfer_to_lot.message_post(
                body=f"Added quantity: {serial_quantity} From: '{self.display_name}' - '{self.serial_number}'")

    def create_transfer(self, lot, picking_type_id=False, product_id=False):
        """ Creates stock.picking Transfer
            Operation Type: Rušiavimas
            Source Location 	Rušiavimas IN
            Destination Location: 	Rušiavimas OUT
        :return transfer quantity
        """
        # TODO: extract to top of function
        ready_palettes = self.palette_ids.filtered(lambda rec: rec.state in "ready")

        ready_quantity = sum(ready_palettes.mapped("quantity"))
        self.transfer_qty = ready_quantity
        logging.info(f"\nReady palettes: {ready_palettes}\nReady quantity {ready_quantity} ")

        for record in self:
            order_lines = []
            # Append order lines and create new transfer with a calibrated plank product
            # product_id = product_id if product_id else record.product_id
            order_lines.append(
                (0, 0,
                 {
                     'product_id': product_id.id,  # Nerušiuotos lameles
                     'lot_id': lot.id,
                     'product_uom': product_id.uom_id.id,
                     'company_id': record.env.user.company_id.id,
                     'name': product_id and product_id.name or record.product_id.name,
                     'location_id': picking_type_id.default_location_src_id.id,  # Rušiavimas IN
                     'location_dest_id': picking_type_id.default_location_dest_id.id,  # Rušiavimas OUT
                     'product_uom_qty': ready_quantity,
                 }
                 ))

            picking_id = record.env['stock.picking'].create({
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
                         f"Destination Location: {picking_type_id.default_location_dest_id.name}\n")
            picking_id.action_confirm()

            # Click 'Availability' button
            picking_id.action_assign()

            # Click 'Validate' button '_action_done' is triggered in 'stock.picking'
            picking_id.button_validate()

            # for palette in ready_palettes:
            #     palette.state = "done"
            return picking_id
            # return display_popup_message(f"OK", f"Moved successfully", display_type="success")

    def action_transfer_sorted(self):
        """
        Transfer From
        Source Location	WH/Stock/Rušiavimas/IN
        Destination Location	WH/Stock/Rušiavimas/OUT
        :return:
        """
        self.transfer_qty = 0

        picking_type_sorting_in_out = self.env.ref(
            "ecowood_sorting.operation_type_sorting")  # Operation type: RUŠIAVIMAS
        # Current opened lot number
        form_lot_id = self.env['stock.production.lot'].search([('name', '=', self.serial_number)], limit=1)

        # TODO: form_lot_id.average_price
        # list_price = self.product.list_price
        # standat_price = self.product.standard_price #(sorting.mode)
        lamels_unsorted = self.env.ref("ecowood_sorting.item_unsorted_lamels_product_template")
        lamels_sorted = self.env.ref("ecowood_sorting.item_sorted_lamels_product_template")
        print(
            f"operation type: {picking_type_sorting_in_out} / {picking_type_sorting_in_out.name}\nold product:{lamels_unsorted} "
            f"new product:{lamels_sorted} / {lamels_sorted.name} ")

        # Operation type: RUŠIAVIMAS
        # Transfer from Rušiavimas/IN to Rušiavimas/OUT
        # Product: Nerušiuotos lamelės (nonchanged)
        stock_picking = self.create_transfer(picking_type_id=picking_type_sorting_in_out, product_id=lamels_unsorted,
                                             lot=form_lot_id)

        print(f"Transfer qty: {self.transfer_qty}")

        # Transfer from one serial to another serial
        # Product: Nerušiuotos lamelės -> Lameles
        ready_palettes = self.palette_ids.filtered(lambda rec: rec.state in "ready")
        self.from_serial_to_serial(old_serial=self.serial_number, new_serials=ready_palettes, record=stock_picking,
                                   unsorted_pallet_lot=form_lot_id)

        for palette in ready_palettes:
            palette.state = "done"
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
