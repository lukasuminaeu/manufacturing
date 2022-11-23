# -*- coding: utf-8 -*-
import logging

from odoo import models, fields
from odoo.addons.ecowood_sorting.sorting.helper_methods import display_popup_message


class SortingWizard(models.TransientModel):
    """
    Wizards to popup after sorting barcode is scanned
    """
    _name = "sorting.wizard"
    _description = "This wizards show unsorted lamels data"
    type = fields.Char(string="Rūšis")
    size = fields.Float(string="Storis (mm)")
    width = fields.Float(string="Plotis (mm)")
    length1 = fields.Float(string="Ilgis (mm)")
    quantity = fields.Float(string="Vienetai")

    current_model = fields.Integer(
        help="Id of current model. This is needed because ofter running barcode scaner parent context is lost.")
    # Active model
    serial = fields.Char(help="Barcode from list view. It's passed to palete_ids")

    def action_send(self):
        """
        Create entry in Sorting History
        """
        parent_model_id = self.env.context.get('active_id')
        if not parent_model_id:
            logging.info(f"Getting model id from wizard")
            parent_model_id = self.current_model
        logging.info(f"parent id {parent_model_id}")
        sorting_model = self.env['sorting.model'].browse(parent_model_id)
        unstopped_time_entry = sorting_model.work_time_ids.filtered(lambda rec: not rec.work_ended)
        number_of_running_timers = len(unstopped_time_entry)
        if number_of_running_timers > 1:  # If there is more then one running jobs
            return display_popup_message("Warning", f"There are still running {number_of_running_timers} jobs")
        if not parent_model_id and not self.quantity:
            return display_popup_message("Error", f"Missing parent_model_id")
        values_to_create = {
            'type': self.type,
            'size': self.size,
            'width': self.width,
            'length1': self.length1,
            'quantity': self.quantity,
            'serial_to': self.serial,
            'palette_history_id': parent_model_id
        }
        if self.quantity < 0:
            return display_popup_message("Warning", f"Can't negative quantity")
        self.env["sorting.saved.operations"].create(values_to_create)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
