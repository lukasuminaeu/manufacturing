# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ReportInvoiceWithPayment(models.AbstractModel):
    _name = 'report.stock.report_deliveryslip'

    @api.model
    def _get_report_values(self, docids, data=None):
        picking_obj = self.env['stock.picking'].browse(docids)
        invoice_id = False
        if picking_obj.origin:
            invoice_id = self.env['account.move'].search([('invoice_origin', '=', picking_obj.origin)])

        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': self.env['stock.picking'].browse(docids),
            'report_type': data.get('report_type') if data else '',
            'invoice_id': invoice_id,
        }
