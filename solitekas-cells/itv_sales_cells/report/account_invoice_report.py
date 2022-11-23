# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ReportInvoiceWithPayment(models.AbstractModel):
    _inherit = 'report.account.report_invoice_with_payments'

    @api.model
    def _get_report_values(self, docids, data=None):
        move_obj = self.env['account.move'].browse(docids)
        order_id = False
        if move_obj.invoice_origin:
            order_id = self.env['sale.order'].search([('name', '=', move_obj.invoice_origin)])

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': self.env['account.move'].browse(docids),
            'report_type': data.get('report_type') if data else '',
            'order_id': order_id,
        }
