# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api
from enum import Enum
_logger = logging.getLogger(__name__)


class StockPickingSplitting(models.Model):

    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        calibrated_boards= self.env.ref("um_lots.item_dried_boards_calibrated_product_template")
        if not self or self.product_id.id != calibrated_boards.id:
            return res
        # calibration = self.env.ref("um_lots.operation_type_send_to_calibration")
        # splitting = self.env.ref("ecowood_splitting.operation_type_transfer_to_splitting")
        # if self.picking_type_id.id == calibration.id:
        #     return self.env['um_lots']._action_done()
        # elif self.picking_type_id.id != splitting.id:
        #     return res
        for record in self:
            lot_name = record.lot_id.name
            lot = record.lot_id
            if not lot_name:
                return res
            lot_form_found = self.env['splitting.model'].search([('serial_number', '=', lot_name)])
            if not lot_form_found:
                picking_type = self.env.ref("ecowood_splitting.operation_type_transfer_to_splitting")
                #stock.move suranda dabartinį įrašą, skirta rasti skaldymo reikšmę
                reference_move = self.env['stock.move'].search([('lot_id','=',lot.id),('picking_type_id',"=",picking_type.id)],limit=1)
                move_lines = self.env['stock.move'].search([('reference','=',reference_move.reference)])
                for line in move_lines:
                    production_lot = self.env['stock.production.lot'].search([('id','=',line.lot_id.id)])
                    form_value = {'product': production_lot.product_id.id,
                                'serial_number': production_lot.name,
                                'created_on': lot.create_date,
                                'length1': production_lot.length1,
                                'width': production_lot.width,
                                'size': production_lot.thickness,
                                'quantity': production_lot.product_qty,
                                'options': line.options,
                                'type_of': production_lot.type_of,
                                'square_meters': production_lot.length1*production_lot.width*production_lot.product_qty/1000000,
                                'state': 'in_progress'
                                }
                    newly_created_lot_form = self.env['splitting.model'].create(form_value)
        return res

    def process_splitting_barcode(self, barcode):
        """
            processes passed through barcode

        """
        class ExtendedEnum(Enum):
            @classmethod
            def list(cls):
                return list(map(lambda c: c.value, cls))
        class OperationType(ExtendedEnum):
            STOP = 'SKALDYMO PABAIGA'
        #if stop find record with state in progress and transfer it
        if barcode == OperationType.STOP.value:
            lots_in_progress = self.env['splitting.model'].search([('state', '=', 'in_progress')])
            if not lots_in_progress:
                logging.info(f"No boards to finish")
                return
            logging.info(f"Reached stop value will check")
            return self.env["splitting.model"].action_transfer_calibrated(lots_in_progress)
        #get all pallete names
        palletes = self.env.ref("um_lots.item_dried_boards_calibrated_product_template")
        pallete_sort_barcode_ids = self.env['stock.production.lot'].search([("product_id", "=", palletes.id)])
        pallete_sort_barcode_names = pallete_sort_barcode_ids.mapped("name")
        if barcode in pallete_sort_barcode_names:
            lot_model = self.env['splitting.model'].search([('serial_number', '=', barcode)],limit=1)
            for lot in lot_model:
                #if any of the records are in progress state, change it back to ready
                for faulty in self.env['splitting.model'].search([('state', '=', 'in_progress')]):
                    faulty.state= 'ready'
                lot.state='in_progress'
                lot.start_time=fields.Datetime.now()
                logging.info(f"changing {lot.state} state to in_progress")
                lot_form_found = self.env['splitting.model'].search([('serial_number', '=', barcode)])
                for rec in self:
                    logging.info(f"changing {self.state} state to in_progress")
                for rec in self.env['splitting.model'].search([]):
                    logging.info(f"lot {rec.serial_number} is in state {rec.state}")
                created = self.env['splitting.popup.model'].create(
                    {'product': f"{palletes.name}",
                    'measurments': f"{lot.length1} x {lot.width} x {lot.size}",
                    'options': f"{lot.options}",
                    'serial': f"{lot.serial_number}"
                    })
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "splitting.popup.model",
                    "views": [[False, "form"]],
                    "res_id": created.id,
                    "target": "new",
                }