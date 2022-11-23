# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError

class ReportPackingList(models.AbstractModel):
    _name = 'report.um_stock_report.report_packinglist'
    _description = 'Packing List Report'

    def _get_report_values(self, docids, data):
        docs = self.env['stock.picking'].browse(docids)
        for d in docs:
            if not d.sale_id:
                raise UserError("This Report can be only used on pickings related to sales")

            if not d.sale_id.invoice_ids:
                raise UserError("This report can be only used on pickings with invoices related")

        return {
            'doc_ids': docs.ids,
            'doc_model': 'stock.picking',
            'data': data,
            'docs': docs,
        }
