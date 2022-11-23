from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = "stock.move"
    
    options = fields.Selection([('x4','x4 (4,5 mm)'), ('x5', 'x5 (3,8 mm)'), ('x6', "x6 (2.5 mm)")], 
                 string = "Skaldymas")
    is_operation_type_skaldymas = fields.Boolean(string="Used to determine view conditions", compute ="_compute_is_operation_type_skaldymas")

    @api.depends("picking_type_id")
    def _compute_is_operation_type_skaldymas(self):
        operation_transfer = self.env.ref("ecowood_splitting.operation_type_transfer_to_splitting")
        self.is_operation_type_skaldymas =  operation_transfer.id == self.picking_type_id.id