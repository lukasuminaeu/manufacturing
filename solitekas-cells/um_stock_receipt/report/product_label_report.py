# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError
import math

def _prepare_data(env, data):
    # change product ids by actual product object to get access to fields in xml template
    # we needed to pass ids because reports only accepts native python types (int, float, strings, ...)
    if data.get('active_model') == 'product.template':
        Product = env['product.template'].with_context(display_default_code=False)
    elif data.get('active_model') == 'product.product':
        Product = env['product.product'].with_context(display_default_code=False)
    else:
        raise UserError(_('Product model not defined, Please contact your administrator.'))

    total = 0
    quantity_by_product = defaultdict(list)
    for p, q in data.get('quantity_by_product').items():
        product = Product.browse(int(p))
        quantity_by_product[product].append((product.barcode, q))
        total += q
    if data.get('custom_barcodes'):
        # we expect custom barcodes format as: {product: [(barcode, qty_of_barcode)]}
        for product, barcodes_qtys in data.get('custom_barcodes').items():
            quantity_by_product[Product.browse(int(product))] += (barcodes_qtys)
            total += sum(qty for _, qty in barcodes_qtys)

    layout_wizard = env['product.label.layout'].browse(data.get('layout_wizard'))
    if not layout_wizard:
        return {}

    lots_count = 0
    for prdct in list(quantity_by_product):
        lots_count += len(quantity_by_product[prdct])

    #Umina edit (Valentas): remade functionality to count pages by number of lots
    #and not quantities
    # page_required = lots_count // (layout_wizard.rows * layout_wizard.columns)
    page_required = math.ceil(lots_count  /  (layout_wizard.rows * layout_wizard.columns)) + 1

    return {
        'quantity': quantity_by_product,
        'rows': layout_wizard.rows,
        'columns': layout_wizard.columns,
        'page_numbers': page_required,
        # 'page_numbers': page_required,
        # 'page_numbers': (total - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
        'price_included': data.get('price_included'),
        'extra_html': layout_wizard.extra_html,
    }

class ReportProductTemplateLabel(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, data)

class CellsReportProductTemplateLabel(models.AbstractModel):
    _name = 'report.um_stock_receipt.cells_report_producttemplatelabel'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, data)

# class ReportProductTemplateLabelDymo(models.AbstractModel):
#     _name = 'report.product.report_producttemplatelabel_dymo'
#     _description = 'Product Label Report'

#     def _get_report_values(self, docids, data):
#         return _prepare_data(self.env, data)
