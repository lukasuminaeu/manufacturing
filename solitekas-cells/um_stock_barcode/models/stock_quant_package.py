
from odoo import api, models, _, fields
from odoo.tools import config
from odoo.tools import format_datetime

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    # This field will handle all the quants that were assigned but not reserved
    move_line_ids = fields.One2many('stock.move.line', 'result_package_id', 'Bulk Content Move Lines', readonly=True)
    
    picking_id_pallet_scrap = fields.Many2one('stock.picking')