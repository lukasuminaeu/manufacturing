
from odoo import models, fields, _, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    proposed_package_quantity = fields.Integer('Proposed Package Quantity', default=0)

    @api.model
    def _get_fields_stock_barcode(self):
        res = super(ProductProduct, self)._get_fields_stock_barcode()
        res.append('proposed_package_quantity')
        return res

    def prefilled_owner_package_stock_barcode(self, lot_id=False, lot_name=False):
        #Umina edit: filter out all quants thats quantity is not more than 0
        #because it was taking old package which in stock.quant was still
        #picked so in barcode module new update of package was not seen.
        quant = self.env['stock.quant'].search_read(
            [
                lot_id and ('lot_id', '=', lot_id) or lot_name and ('lot_id.name', '=', lot_name),
                ('location_id.usage', '=', 'internal'),
                ('product_id', '=', self.id),
            ],
            ['package_id', 'owner_id', 'quantity'],
            # ['package_id', 'owner_id'],
            load=False
            # limit=1, load=False
        )

        quant = list(filter(lambda x: x['quantity'] > 0, quant))

        if quant:
            quant = quant[0]
        res = {'quant': quant, 'records': {}}
        if quant and quant['package_id']:
            res['records']['stock.quant.package'] = self.env['stock.quant.package'].browse(quant['package_id']).read(self.env['stock.quant.package']._get_fields_stock_barcode(), load=False)
        if quant and quant['owner_id']:
            res['records']['res.partner'] = self.env['res.partner'].browse(quant['owner_id']).read(self.env['res.partner']._get_fields_stock_barcode(), load=False)

        return res