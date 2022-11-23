from odoo import models, fields, api
from odoo.tools import float_compare, float_round, format_datetime
from odoo.exceptions import UserError

from odoo import models, fields, api


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def _update_finished_move(self):
        """ Update the finished move & move lines in order to set the finished
        product lot on it as well as the produced quantity. This method get the
        information either from the last workorder or from the Produce wizard."""
        production_move = self.production_id.move_finished_ids.filtered(
            lambda move: move.product_id == self.product_id and
                         move.state not in ('done', 'cancel')
        )
        if not production_move:
            return
        if self.production_id.current_variation_id != self.production_id.product_id:
            production_move.product_id = self.production_id.current_variation_id

        if production_move.product_id.tracking != 'none':
            if not self.finished_lot_id:
                raise UserError(_('You need to provide a lot for the finished product.'))
            move_line = production_move.move_line_ids.filtered(
                lambda line: line.lot_id.id == self.finished_lot_id.id
            )
            if move_line:
                if self.product_id.tracking == 'serial':
                    raise UserError(_('You cannot produce the same serial number twice.'))
                move_line.product_uom_qty += self.qty_producing
                move_line.qty_done += self.qty_producing
            else:
                quantity = self.product_uom_id._compute_quantity(self.qty_producing, self.product_id.uom_id, rounding_method='HALF-UP')
                putaway_location = production_move.location_dest_id._get_putaway_strategy(self.product_id, quantity)
                move_line.create({
                    'move_id': production_move.id,
                    'product_id': production_move.product_id.id,
                    'lot_id': self.finished_lot_id.id,
                    'product_uom_qty': self.qty_producing,
                    'product_uom_id': self.product_uom_id.id,
                    'qty_done': self.qty_producing,
                    'location_id': production_move.location_id.id,
                    'location_dest_id': putaway_location.id,
                })
        else:
            rounding = production_move.product_uom.rounding
            production_move._set_quantity_done(
                float_round(self.qty_producing, precision_rounding=rounding)
            )