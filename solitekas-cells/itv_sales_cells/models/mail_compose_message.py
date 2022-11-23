# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import base64
import logging

_logger = logging.getLogger(__name__)


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        # Override
        super(MailComposer, self).onchange_template_id_wrapper()
        self.ensure_one()
        values = self.onchange_template_id(self.template_id.id, self.composition_mode, self.model, self.res_id)['value']
        _logger.debug('\n\n %s \n\n', 'testing invoice')

        # if self.env.context.get('active_model') != 'account.move':
            # -------------Add to Email (Invoice, Pro-Forma)------
        attach_ids = self._add_custom_attachments(self.res_id)
        values['attachment_ids'] = [(6, 0, attach_ids)]
        # ----------------------------------------------------

        for fname, value in values.items():
            setattr(self, fname, value)

    # Add Custom attachments To Email
    def _add_custom_attachments(self, res_id):
        _logger.debug('\n\n %s %s\n\n', '1', res_id)
        if self.env.context.get('active_model') != 'account.move':
            sale_order = self.env['sale.order'].browse(res_id)
            _logger.debug('\n\n %s %s %s \n\n', '2', self.env.context, sale_order)
            if self.env.context.get('proforma'):
                invoice_pdf = self.env.ref('sale.action_report_pro_forma_invoice').render_qweb_pdf([res_id])[0]
                invoice_pdf = base64.b64encode(invoice_pdf)
            else:
                invoice_pdf = self.env.ref('sale.action_report_saleorder').render_qweb_pdf([res_id])[0]
                invoice_pdf = base64.b64encode(invoice_pdf)
            _logger.debug('\n\n %s \n\n', 'testing adding attachment')
            if self.env.context.get('proforma'):
                list_values = [('PRO-FORMA_%s.pdf' % sale_order.name, invoice_pdf)]
            elif self.env.context.get('model_description') == 'Sales Order':
                list_values = [('Order_%s.pdf' % sale_order.name, invoice_pdf)]
            else:
                list_values = [('Quotation_%s.pdf' % sale_order.name, invoice_pdf)]
            # list_values = [('%s_quotation.pdf' % sale_order.name, invoice_pdf),
            #                ('%s_pro_forma.pdf' % sale_order.name, pro_forma_invoice_pdf)]
        if self.env.context.get('active_model') == 'account.move':
            sale_order = self.env['account.move'].browse(res_id)
            invoice_pdf = self.env.ref('account.account_invoices').render_qweb_pdf([res_id])[0]
            invoice_pdf = base64.b64encode(invoice_pdf)
            list_values = [('INVOICE_%s.pdf' % sale_order.name, invoice_pdf)]

        _logger.debug('\n\n wtf %s \n\n', self.env.context)
        attach_ids = []
        attachment = self.env['ir.attachment']
        for store_fname, attach_datas in list_values:
            data_attach = {
                'name': store_fname,
                'datas': attach_datas,
                'store_fname': store_fname,
                'res_model': 'mail.compose.message',
                'res_id': 0,
                'type': 'binary',
            }
            attach_ids.append(attachment.create(data_attach).id)

        return attach_ids
