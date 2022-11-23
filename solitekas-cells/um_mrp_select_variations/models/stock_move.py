from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    original_product_uom_qty = fields.Float("Product UoM Qty Original")
    original_product = fields.Many2one('product.product','Original Product', help='Product before changing variation')


    def test123(self):
        print('qwe123')  
        print(self.reserved_availability)  