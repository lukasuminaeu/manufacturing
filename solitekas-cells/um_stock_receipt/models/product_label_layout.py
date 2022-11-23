# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models

class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7xprice', '2 x 7 with price'),
        ('4x7xprice', '4 x 7 with price'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 with price'),
        ('1x1xprice', 'Solitek Cells')], string="Format", default='1x1xprice', required=True)

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()
        if 'zpl' in self.print_format:
            xml_id = 'stock.label_product_product'
        elif self.print_format == '1x1xprice':
            #Umina edit: use custom report template
            xml_id = 'um_stock_receipt.report_product_template_label_cells_test'

        if self.picking_quantity == 'picking' and self.move_line_ids:
            qties = defaultdict(int)
            custom_barcodes = defaultdict(list)
            uom_unit = self.env.ref('uom.product_uom_categ_unit', raise_if_not_found=False)
            for line in self.move_line_ids:
                #Umina edit (Valentas): commenting out below conditional, because
                #it was not printing out barcodes for 'uom' others than 'Unit'
                #for example - m, cm... uoms barcodes were not displayed in pdf.
                # if line.product_uom_id.category_id == uom_unit:
                    #Umina edit (Valentas): Changed it to not format as int(line.qty_done)
                    #because it was skipping 0.1 values then.
                    if (line.lot_id or line.lot_name) and line.qty_done:
                    # if (line.lot_id or line.lot_name) and int(line.qty_done):
                        custom_barcodes[line.product_id.id].append((line.lot_id.name or line.lot_name, int(line.qty_done)))
                        continue
                    qties[line.product_id.id] += line.qty_done
            # Pass only products with some quantity done to the report
            data['quantity_by_product'] = {p: int(q) for p, q in qties.items() if q}
            data['custom_barcodes'] = custom_barcodes
        return xml_id, data
