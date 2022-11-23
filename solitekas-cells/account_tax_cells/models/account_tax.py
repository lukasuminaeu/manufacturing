# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models,fields, _


import logging
_logger = logging.getLogger(__name__)


class Tax(models.Model):
    _inherit = "account.tax"

    tax_paragraph = fields.Text(string='Tax Article', translate=True)


class Invoice(models.Model):
    _inherit = "account.move"

    tax_paragraph = fields.Text(string='Tax Paragraph', compute='_compute_tax_paragraph')

    def _compute_tax_paragraph(self):
        paragraph = []
        for record in self:
            for line in record.invoice_line_ids:
                for tax in line.tax_ids:
                    if tax.tax_paragraph and tax.tax_paragraph not in paragraph:
                        paragraph.append(tax.tax_paragraph)
        self.tax_paragraph = ("").join(paragraph)
