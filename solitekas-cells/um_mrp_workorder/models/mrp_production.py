# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_compare
from odoo.tools.misc import format_date
import math


class MrpWorkorder(models.Model):
    _inherit = 'mrp.production'

    @api.depends('state', 'move_raw_ids.state', 'move_raw_ids.move_line_ids.product_uom_qty')
    def _compute_reservation_state(self):
        self.reservation_state = False
        for production in self:
            if production.state in ('draft', 'done', 'cancel'):
                continue
            relevant_move_state = production.move_raw_ids._get_relevant_state_among_moves()
            # Compute reservation state according to its component's moves.
            if relevant_move_state == 'partially_available':
                if production.workorder_ids.operation_id and production.bom_id.ready_to_produce == 'asap':
                    production.reservation_state = production._get_ready_to_produce_state()
                else:
                    production.reservation_state = 'confirmed'
            elif relevant_move_state != 'draft':
                production.reservation_state = relevant_move_state


            # Adding this functionality, because if there is enough components reserved atleast for
            # one product to be produced, then make the state of workorder to be ready instead of waiting for components
            lst = []
            for tst in production.move_raw_ids:
                if sum(tst.move_line_ids.mapped('product_uom_qty')) >= tst.bom_line_id.product_qty:
                    lst.append(True)
                else:
                    lst.append(False)

            if all(lst):
                production.reservation_state = 'assigned'
            # production.env['bus.bus']._sendone('mrp_production', 'workorder_update', {})
            # production.env['bus.bus']._sendone('mrp_workorder', 'workorder_update', {})

    def update_component_qty_workorder(self):
        """This method is needed to set 'qty_done' of workorder of current component
            to the value that we have in a quant domain table, because if we dont use this method
            then 'qty_done' will be set automatically, so that will be incorrect value."""
        for workorder in self.workorder_ids:
            if workorder.lot_id:
                if workorder.component_tracking == 'lot':
                    component_in_table = workorder.component_stock_quant_domain.filtered(lambda x: x.lot_id == workorder.lot_id)
                    if component_in_table:
                        workorder.qty_done = component_in_table.quantity

    
    def action_assign(self):
        # Edvardas ADD: on click of 'Check Availability', we want the system
        # to update availability of all child production orders
        #Initiate assign on child manufacturing orders only if button was clicked.

        # if 'button_click' in self._context:
        #     self = self + self.child_production_ids

        for production in self:
            move_raw_ids = production.mapped('move_raw_ids').filtered(lambda x: x.state not in ('done', 'cancel'))
            move_raw_ids._action_assign()
            #Check if production order is not in process yet, only then we can
            #change produced qty.
            if all(production.mapped('workorder_ids.is_first_step')):
                production.compute_available_qty_set_workorder()

            # production.env['bus.bus']._sendone('mrp_production', 'workorder_update', {})
            # production.env['bus.bus']._sendone('mrp_workorder', 'workorder_update', {})
        return True


    def compute_available_qty_set_workorder(self):
        for production in self:
            if production.product_id.tracking not in ('serial'):
                move_raw_ids = production.mapped('move_raw_ids').filtered(lambda x: x.state not in ('done', 'cancel'))

                def auto_consumed_products_correction(move, possible_qty_producing):
                    """If there was auto consumed products in MO, then rewrite
                    that consumed field by reserved availability. Because of the new functioning
                    recalculating possible production it was not recomputing auto consumed components."""
                    
                    #Only apply it for lines with quantity_done more than zero, because
                    #this will apply only for first WO step anyway.
                    # if move.quantity_done > 0:
                    #     move.quantity_done = move.reserved_availability
                    move.quantity_done = possible_qty_producing

                def compute_possible_quantity_produce(product_qty, reserved_qty, full_qty_produce, move):
                    possible_qty_producing = product_qty * reserved_qty / full_qty_produce
                    #Adding rounding here, because it was getting weird float sometimes
                    #like 1.0999999999 and that was not accurate
                    possible_qty_producing = round(possible_qty_producing, 8)
                    possible_qty_producing = math.floor(possible_qty_producing)


                    if move.product_id.tracking == 'none':
                        auto_consumed_products_correction(move, possible_qty_producing)
                    
                    return possible_qty_producing

                product_qty = production.product_qty
                possible_qty_producing = [compute_possible_quantity_produce(product_qty, mv.reserved_availability, mv.product_uom_qty, mv) for mv in move_raw_ids]
                if possible_qty_producing:
                    # move_raw_ids.raw_material_production_id.qty_producing = min(possible_qty_producing)
                    production.qty_producing = min(possible_qty_producing)
                    for wo in production.workorder_ids:
                        wo.qty_producing = min(possible_qty_producing)

                        #Update currently registering component qty, because 
                        #it doesnt get updated automatically after changing
                        #wo.qty_producing.
                        if wo.component_remaining_qty:
                            component_qty = wo.move_id.bom_line_id.product_qty * wo.qty_producing
                            wo.qty_done = component_qty

                production.update_component_qty_workorder()

    
    def action_cancel(self):
        """ Cancels production order, unfinished stock moves and set procurement
        orders in exception """
        # Edvardas ADD: on click of 'Cancel', we want the system
        # to cancel all child production orders
        ### TODO
        # Should we cancel 'progress' MOs or leave them?
        # What should happen with produced intermediate products?
        # What should happen with raw materials in the VBZ?
        for production in self + self.child_production_ids:
            production._action_cancel()
            # production.env['bus.bus']._sendone('mrp_production', 'workorder_update', {})
            # production.env['bus.bus']._sendone('mrp_workorder', 'workorder_update', {})
        return True


    @api.depends('state', 'reservation_state', 'date_planned_start', 'move_raw_ids', 'move_raw_ids.forecast_availability', 'move_raw_ids.forecast_expected_date')
    def _compute_components_availability(self):
        productions = self.filtered(lambda mo: mo.state not in ('cancel', 'done', 'draft'))
        productions.components_availability_state = 'available'
        productions.components_availability = _('Available')

        other_productions = self - productions
        other_productions.components_availability = False
        other_productions.components_availability_state = False

        all_raw_moves = productions.move_raw_ids
        # Force to prefetch more than 1000 by 1000
        all_raw_moves._fields['forecast_availability'].compute_value(all_raw_moves)
        for production in productions:
            if any(float_compare(move.forecast_availability, 0 if move.state == 'draft' else move.product_qty, precision_rounding=move.product_id.uom_id.rounding) == -1 for move in production.move_raw_ids):
                production.components_availability = _('Not Available')
                production.components_availability_state = 'late'
            else:
                forecast_date = max(production.move_raw_ids.filtered('forecast_expected_date').mapped('forecast_expected_date'), default=False)
                if forecast_date:
                    production.components_availability = _('Exp %s', format_date(self.env, forecast_date))
                    if production.date_planned_start:
                        production.components_availability_state = 'late' if forecast_date > production.date_planned_start else 'expected'

            #If there is enough components to produce atleast one qty of product
            if production.reservation_state == 'assigned' or production.components_availability_state == 'available': 
                production.components_availability = 'Available'
