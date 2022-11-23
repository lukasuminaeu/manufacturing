# -*- coding: utf-8 -*-

from odoo import models, fields


class SortingWizard(models.TransientModel):
    """
    Wizards to popup after sorting barcode is scanned
    """
    _name = "detailed.operation.wizard"
    _description = "wizard for debugging purposes"
    product = fields.Char(string="Product")
    demand = fields.Float(string="Demand")
    quantity_done = fields.Float(string="Quantity Done")

    move_line = fields.One2many('res.company', 'parent_id', string='Test field')

    def action_send(self):
        print("Test confirm info")
