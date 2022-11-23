# -*- coding: utf-8 -*-

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_open_picking_client_action(self):
        action = super().action_open_picking_client_action()
        if 'barcode_open_line' in self._context:
            action['context']['barcode_open_line'] = True

        return action

    def ecowood_assign_confirm_picking(self):
        for record in self:
            if record.state not in ('assigned', 'done'):
                record.action_assign()
            if record.state not in 'done':
                record.button_validate()

                # Set calibration end state
                # Set end date
                record.lot_id.calibration_state = "done"
                record.end_time = fields.Datetime.now()
        return

    def action_kalibration_view(self):
        """
        When calibration is ended redirect to calibration view
        """
        action = self.env.ref('um_lots.action_picking_tree_all_inherit').read()[0]
        action['target'] = 'main'
        action['views'] = [(False, 'list'), (False, 'form')]
        return action
