# -*- coding: utf-8 -*-
import datetime
import logging

from odoo import models, fields
from odoo.addons.ecowood_sorting.sorting.helper_methods import display_popup_message

_logger = logging.getLogger(__name__)

from enum import Enum


class StockPickingSorting(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        if not self:
            return res
        for record in self:
            barcode = record.lot_id.name
            lot = record.lot_id
            # If we have no barcode skip
            if not barcode:
                return res
            # OPERATION TYPE: Ecowood ecowood: Receipts BUY
            unsorted_lamels = self.env.ref('ecowood_sorting.operation_type_sort_bought')

            if record.picking_type_id == unsorted_lamels:
                logging.info(f"Creating new lot form entry for: {record}")
                # TODO no record.product_qty ADD> Also is this correct barcode
                form_value = {'product': record.product_id.id,
                              'serial_number': barcode,
                              'created_on': record.create_date,
                              'length1': record.length1,
                              'width': record.width,
                              'size': record.thickness,
                              "type_of": record.type_of,
                              'quantity': ''}
                newly_created_lot_form = self.env['sorting.model'].create(form_value)
                logging.info(f"Created new element in sorting lamels: {newly_created_lot_form.id}")
                return res

            unsorted_lamels = self.env.ref('ecowood_sorting.item_unsorted_lamels_product_template')
            if unsorted_lamels.id != lot.product_id.id:
                return res

            lot_form_found = self.env['sorting.model'].search([('serial_number', '=', barcode)])

            if not lot_form_found:
                # Create sorting.model entry
                logging.info(f"Creating new lot form entry for: {lot}")
                # square_meters = (lot.length * lot.width) / 100
                fixed_average_price = self.calculate_average(lot.palette_price, lot.quantity_squared)
                logging.info(f"fixed_average_price: {fixed_average_price}")
                form_value = {'product': lot.product_id.id,
                              'serial_number': barcode,
                              'created_on': lot.create_date,
                              'length1': lot.length1,
                              'width': lot.width,
                              'size': lot.thickness,
                              'quantity': lot.product_qty,
                              'fixed_average_price': fixed_average_price,
                              'fixed_total_price': lot.palette_price,
                              "type_of": lot.type_of,
                              }
                newly_created_lot_form = self.env['sorting.model'].create(form_value)
                logging.info(f"Created new element in sorting lamels: {newly_created_lot_form.id}")
                return res

    def calculate_average(self, price, quantity):
        """
        Calculate average square meters price
        """
        try:
            average_price = price / quantity
            logging.info(f"Average square meter price: {price} /  square_meters {quantity} =  {average_price}")

            return average_price
        except ZeroDivisionError:
            logging.warning(f"Decision by zero error in '{self}'")
            return 0

    def list_barcode_scanned(self, barcode):
        """
        This view process on calibration view
        :param barcode: barcode from list view
        """
        if barcode == "O-CMD.TEST":
            return
        return self.process_view_calibration(barcode)

    def process_view_calibration(self, barcode):

        operation_type_calibration = self.env.ref("um_lots.operation_type_calibration")
        is_debug = self.user_has_groups('ecowood_sorting.group_dev')

        class ExtendedEnum(Enum):

            @classmethod
            def list(cls):
                return list(map(lambda c: c.value, cls))

        class OperationType(ExtendedEnum):
            CALIBRATION_END = "KALIBRAVIMO PABAIGA"
            CMD_CONFIRM = "O-CMD.CONFIRM"
        # End calibration move to barcode window

        if barcode == OperationType.CMD_CONFIRM.value:
            #Confirm picking
            return

        if barcode == OperationType.CALIBRATION_END.value:
            stock_moves = self.env['stock.move'].search([
                ('picking_type_id', '=', operation_type_calibration.id),
                ('state', 'not in', ('cancel', 'done'))
            ])
            if not stock_moves:
                return display_popup_message(title="Klaida", message="Nėra įrašų")
            filter_with_start_time = stock_moves.picking_id.filtered(lambda r: r.start_time and not r.end_time)
            for picking in filter_with_start_time:
                barcode = picking.calibrating_lot
                lot_id = self.env['stock.production.lot'].search([
                    ('name', '=', barcode),
                    ('calibration_state', '=', 'in_progress'),
                ], limit=1)

                stock_move = self.env['stock.picking'].search(
                    [
                        ('picking_type_id', '=', operation_type_calibration.id),
                        ('calibrating_lot', '=', lot_id.display_name),
                        ('state', 'not in', ['done', 'cancel']),

                    ], limit=1)
                if not stock_moves:
                    return display_popup_message(title="Klaida", message="Nėrasti įrašai")
                action = stock_move.with_context(
                    barcode_open_line=True).action_open_picking_client_action()
                return action
            return display_popup_message(title="Klaida", message="Kalibravimas baigtas")

        # Start calibration after scanning barcode
        # If lot exists start calibration timer
        lot_id = self.env['stock.production.lot'].search([
            ('name', '=', barcode),
            ('calibration_state', 'not in', ['done']),
        ], limit=1)
        if lot_id:
            picking = self.env['stock.picking'].search(
                [
                    ('picking_type_id', '=', operation_type_calibration.id),
                    ('lot_id', '=', lot_id.id),
                    ('state', 'not in', ['done', 'cancel']),

                ], limit=1)
            if not picking:
                return display_popup_message(title="Klaida", message="Nerastas kalibracijos įrašas")
            if not picking.start_time:
                picking.start_time = datetime.datetime.now()
                picking.calibrating_lot = barcode

                if is_debug:
                    logging.info("-----------------------------")
                    logging.info("DEBUG MODE")
                    logging.info("-----------------------------")
                    lot_id.calibration_state = "in_progress"
                else:
                    lot_id.calibration_state = "in_progress"
            else:
                return display_popup_message(title="Klaida", message="Kalibravimas pradėtas")
        else:
            return display_popup_message(title="Klaida", message="Nerasta arba uždaryta paletė")
        return {
            'type': 'ir.actions.act_view_reload'
        }

    def process_barcode(self, barcode):
        """
        Process barcode in sorting view
        Display form after barcode is scanned
        Process sorting operations
        """
        lot = self.env['stock.production.lot'].search([('name', '=', barcode)])
        if not lot:
            logging.warning(f"Missing serial lot: {barcode}")
            title = f"Serial '{barcode}' number missing"
            message = "Can't open non existing serial lot"
            return display_popup_message(title, message)

        lot_form_found = self.env['sorting.model'].search([('serial_number', '=', barcode)])
        if not lot_form_found:
            return display_popup_message(f"Error", f"Can't open. This: '{barcode}' lot not found.")

        logging.info(f"Processing lot number: {lot}")
        if lot_form_found.state in ['done']:
            return display_popup_message(f"Error", f"Can't open. This: '{barcode}' lot is Done")

        current_lot = lot_form_found

        first_time_work = False
        if not current_lot.work_time_ids:
            # If there is no start working time
            current_lot.init_timer()
            self.add_work_history_entry(current_lot)
            first_time_work = True

        if not first_time_work:
            unstopped_time_entry = current_lot.work_time_ids.filtered(lambda rec: not rec.work_ended)
            if unstopped_time_entry:
                logging.warning(f"There are still running jobs\n{unstopped_time_entry}")
            if lot_form_found and not unstopped_time_entry:
                if lot_form_found.stop_time:
                    self.add_work_history_entry(lot_form_found)

        form_view = {
            "type": "ir.actions.act_window",
            "res_model": "sorting.model",
            "views": [[False, "form"]],
            "res_id": current_lot.id,
            "target": "main",
            'context': {'form_view_initial_mode': 'edit', 'force_detailed_view': 'true'},

        }
        logging.info(f"Opening lot from database:\n{form_view}")
        if lot_form_found.timer_pause:
            lot_form_found.action_timer_resume()
        return form_view

    def add_work_history_entry(self, newly_created_lot_form):
        work_values = {
            "work_started": fields.Datetime.now(),
            "worker": self.user_id.id,
            "work_time_id": newly_created_lot_form.id,
        }
        logging.info(f"Creating record for initial start time")
        self.env['sorting.saved.time'].create(work_values)
