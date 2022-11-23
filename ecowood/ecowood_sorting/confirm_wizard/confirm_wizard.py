# -*- coding: utf-8 -*-

from odoo import models, fields


class ConfirmTransactionWizard(models.TransientModel):
    """
    Confirms transaction
    """
    _name = "confirm.wizard"
    _description = "Confirm wizard"

    source_document = fields.Integer(help="Source document, from which its called")

    def click_confirm(self):
        """
        Action that is processed after confirm wizard button is clicked
        :return:
        """
        sorting_model = self.env["sorting.model"].browse(self.source_document)
        return sorting_model.action_transfer_sorted()
