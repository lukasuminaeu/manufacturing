from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class BZ(models.Model):
    _inherit = 'mrp.production'

    is_final_product = fields.Boolean(related='product_id.is_final_product')

    def write(self, vals):
        res = super().write(vals)
        #Set child production ids picking_ids 'origin' field to main_production_id name.
        if 'main_production_id' in vals:
            if len(self.procurement_group_id.mrp_production_ids) == 1:
                picking_ids = self.env['stock.picking'].search([
                    ('group_id', '=', self.procurement_group_id.id), ('group_id', '!=', False),
                ])
                picking_ids.origin = self.main_production_id.name

        return res

    def change_date_planned(self):
        """
        This function is called on click of 'Change date' button in mrp.production form view.
        The aim is to change all child production order dates if final product order date is changed.
        """
        new_date = self.date_planned_start
        move_ids = self.env['stock.move']
        picking_ids = self.env['stock.picking']

        for production in self + self.child_production_ids:
            move_ids += production.move_raw_ids
            move_ids += production.move_finished_ids
            picking_ids += production.env['stock.picking'].search([('origin','=',production.name)]).filtered(lambda c: c.state not in ('done', 'cancel'))
            move_ids += picking_ids.move_lines

        #Umina (Valentas) edit:
        #Dont initiate write function, if the written value
        #is same as the fields value, because it creates loop later
        #in write method
        for child_prod in self.child_production_ids:
            if new_date != child_prod.date_planned_start or \
            new_date != child_prod.date_deadline or \
            new_date != child_prod.date_planned_finished:
                self.child_production_ids.write({'date_planned_start': new_date, 'date_deadline': new_date, 'date_planned_finished': new_date})
                move_ids.write({'date': new_date, 'date_deadline': new_date})
                picking_ids.write({'scheduled_date':new_date})

        # self.child_production_ids.write({'date_planned_start': new_date, 'date_deadline': new_date, 'date_planned_finished': new_date})
        # move_ids.write({'date': new_date, 'date_deadline': new_date})
        # picking_ids.write({'scheduled_date':new_date})

    def action_confirm(self):
        self._check_company()
        for production in self:
            if production.bom_id:
                production.consumption = production.bom_id.consumption
            # In case of Serial number tracking, force the UoM to the UoM of product
            if production.product_tracking == 'serial' and production.product_uom_id != production.product_id.uom_id:
                production.write({
                    'product_qty': production.product_uom_id._compute_quantity(production.product_qty, production.product_id.uom_id),
                    'product_uom_id': production.product_id.uom_id
                })
                for move_finish in production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id):
                    move_finish.write({
                        'product_uom_qty': move_finish.product_uom._compute_quantity(move_finish.product_uom_qty, move_finish.product_id.uom_id),
                        'product_uom': move_finish.product_id.uom_id
                    })
            production.move_raw_ids._adjust_procure_method()
            
            (production.move_raw_ids | production.move_finished_ids)._action_confirm(merge=False)
            production.workorder_ids._action_confirm()
        # run scheduler for moves forecasted to not have enough in stock
        self.move_raw_ids._trigger_scheduler()
        self.picking_ids.filtered(
            lambda p: p.state not in ['cancel', 'done']).action_confirm()
        # Force confirm state only for draft production not for more advanced state like
        # 'progress' (in case of backorders with some qty_producing)
        self.filtered(lambda mo: mo.state == 'draft').state = 'confirmed'

        # UMINA: Create an internal transfer on creation of a manufacturing order. 
        # Cannot use Inventory Routings because of clashes with MPS and the complex structure of transfers
        self.procure_components()

        # UMINA: Current Variation should never be empty when production order is confirmed.
        # That is why, on confirmation, we set current_variation_id == product_id.
        self.set_current_variation()

        if len(self.procurement_group_id.mrp_production_ids) == 1:
            self.get_child_production_ids()

        # self.do_unreserve()
        return True

    def procure_components(self):
        for production in self:
            # 'and not production.delivery_count and not production.backorder_sequence' are very important
            # because otherwise we will have a transfer created on every backorder split
            if production.product_id and production.product_id.buffer_zone_id and not production.delivery_count and not production.backorder_sequence:
                # stock_picking = production.env['stock.picking'].search([('origin','=',production.name)])
                components_for_procurement = production.bom_id.bom_line_ids.filtered(lambda l: not l.child_bom_id)
                if components_for_procurement:
                # if not stock_picking and components_for_procurement:
                    stock_picking = production.env['stock.picking'].create({
                        'name': production.name,
                        'picking_type_id': production.env.ref('um_mrp_data.operation_type_buferine_zona').id,
                        'location_id': production.env.ref('um_mrp_data.stock_location_sandelis').id,
                        'location_dest_id': production.product_id.buffer_zone_id.id,
                        'origin': production.name,
                        'scheduled_date': production.date_planned_start,
                        'date_deadline': production.date_planned_start
                    })
                    for component_line in components_for_procurement:

                        stock_move = production.env['stock.move'].create({
                            'name': production.name,
                            'reference': production.name,
                            'location_id': production.env.ref('um_mrp_data.stock_location_sandelis').id,
                            'location_dest_id': production.product_id.buffer_zone_id.id,
                            'picking_id': stock_picking.id,
                            'group_id': production.procurement_group_id.id,
                            'product_id': component_line.product_id.id,
                            'product_uom': component_line.product_id.uom_id.id,
                            'product_uom_qty': component_line.product_qty*production.product_qty,
                            'date': production.date_planned_start,
                            'date_deadline': production.date_planned_start
                        })
                    stock_picking.action_confirm()

class BZStockLocation(models.Model):
    _inherit = 'stock.location'

    # This is excessive, we could use self.env.ref. TODO
    is_picking_zone = fields.Boolean('Is Picking Zone')