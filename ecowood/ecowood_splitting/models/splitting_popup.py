import logging
from odoo.addons.ecowood_sorting.sorting.helper_methods import display_popup_message
from odoo import models, fields
from enum import Enum
_logger = logging.getLogger(__name__)


class SplittingPopup(models.TransientModel):
    _name = "splitting.popup.model"
    _description = "Pop up wizard to show operator production information"
    display_name = fields.Char(string="nff")
    product = fields.Char(string="Produktas")
    measurments = fields.Char(string="Išmatavimai")
    options = fields.Selection([('x4','x4 (4,5 mm)'), ('x5', 'x5 (3,8 mm)'), ('x6', "x6 (2.5 mm)")], 
            string = "Skaldymo nurodymai")
    serial = fields.Char(help="Barcode from list view. It's passed to palete_ids")

    def list_barcode_scanned(self, barcode):
        pass

    def form_barcode_scanned(self, barcode):
        pass