from odoo import models, fields, api, tools, _

_
class StockScrapLine(models.TransientModel):
    _name = 'stock.scrap.line'
    _description = 'Scrap lines model used for multiple components scrap at once'
    
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    scrap_all_wizard = fields.Many2one('scrap.all.wizard')
    scrap_id = fields.Many2one('stock.scrap')
    product_id = fields.Many2one('product.product', domain="[('id', 'in', context.get('product_ids'))]", required=True)
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id), ('id', 'in', available_lot_ids)]", 
        check_company=True)
    available_lot_ids = fields.One2many('stock.production.lot', compute="_compute_available_lot_ids")
    
    scrap_qty = fields.Float()
    uom_id = fields.Many2one('uom.uom', string="UOM", related='product_id.uom_id')
    related_stock_move = fields.Many2one('stock.move')
    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location',
        domain="[('company_id', 'in', [company_id, False]), ('scrap_location', '=', True)]", states={'done': [('readonly', True)]}, check_company=True
        , required=True)
    # scrap_this_component = fields.Boolean(string='Scrap', default=True)

    @api.depends('product_id')
    def _compute_available_lot_ids(self):
        # Compute available lots for scraping. It comes from product lots, that was reserved 
        #for current MO
        for record in self:
            record.available_lot_ids = False
            record.available_lot_ids = record.related_stock_move.move_line_ids.mapped('lot_id')