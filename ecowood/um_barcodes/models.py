import logging
from odoo import models

_logger = logging.getLogger(__name__)


def list_barcode_scanned(self, barcode):
    _logger.info("Barcode scanned: %s" % str(barcode))
    pass

def form_barcode_scanned(self, barcode):
    _logger.info("Barcode scanned: %s" % str(barcode))
    pass


models.BaseModel.list_barcode_scanned = list_barcode_scanned
models.BaseModel.form_barcode_scanned = form_barcode_scanned
