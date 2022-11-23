from odoo.addons.ecowood_sorting.sorting.helper_methods import display_popup_message
from odoo import models, fields
from enum import Enum


class SortingPopup(models.Model):
    _name = "sorting.popup.model"
    _description = "This lets add data to be processed for sorting instead of wizard"
    type = fields.Char(string="Rūšis")
    size = fields.Float(string="Storis (mm)")
    width = fields.Float(string="Plotis (mm)")
    length1 = fields.Float(string="Ilgis (mm)")
    quantity = fields.Float(string="Vienetai")

    current_model = fields.Integer(
        help="Id of current model. This is needed because ofter running barcode scaner parent context is lost.")
    # Active model
    serial = fields.Char(help="Barcode from list view. It's passed to palete_ids")



    def form_barcode_scanned(self, barcode):
        class ExtendedEnum(Enum):

            @classmethod
            def list(cls):
                return list(map(lambda c: c.value, cls))

        class OperationType(ExtendedEnum):
            CONFIRM_MOVE = "PATVIRTINTI PADEJIMA"
            STOP = 'SUSTABDYTI'
            CLOSE = 'UZDARYTI'
            ADD_SORTING = 'PRIDĖTI'

        print("Test from sorting.popup.model")
        if barcode == OperationType.ADD_SORTING.value:
            return self.action_send()

        if barcode.startswith("add"):
            print("Add functionality")
            try:
                number_to_add = float(barcode.split("add")[1])
            except Exception as e:
                print(f"Exception {e}")
            self.quantity += number_to_add
            print(f"Add to wizard {number_to_add}")

        return {
            "type": "ir.actions.act_window",
            "res_model": "sorting.popup.model",
            "views": [[False, "form"]],
            "res_id": self.id,
            "target": "new",
        }

    def action_send(self):
        parent_model_id = self.env.context.get('active_id')

        values_to_create = {
            'type': self.type,
            'size': self.size,
            'width': self.width,
            'length1': self.length1,
            'quantity': self.quantity,
            'serial_to': self.serial,
            'palette_history_id': self.current_model
        }
        if self.quantity < 0:
            return display_popup_message("Warning", f"Can't negative quantity")
        self.env["sorting.saved.operations"].create(values_to_create)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
