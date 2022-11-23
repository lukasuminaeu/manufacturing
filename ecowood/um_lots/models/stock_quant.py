import logging
from odoo import fields, models
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    thickness = fields.Float(related='lot_id.thickness', string='Storis (mm)', store=True)
    width = fields.Float(related='lot_id.width', string='Plotis (mm)', store=True)
    length1 = fields.Float(related='lot_id.length1', string='Ilgis (mm)', store=True)
    volume = fields.Float(related='lot_id.volume', string='Apimtis (m3)', store=True)
    average_price = fields.Monetary(related='lot_id.average_price', string='Average Price')
    calibration_spoilage = fields.Float(related='lot_id.calibration_spoilage', string='Brokas')
