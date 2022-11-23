from ntpath import realpath
from odoo import models, fields, api, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.tools import float_compare, is_html_empty

class TypeOfFault(models.Model):
    _name = 'fault.type'
    _description = 'Type of Fault'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(string='Name', required=True)

class UminaRepairLine(models.Model):
    _inherit = 'repair.line'

    price_unit = fields.Float('Unit Price', required=False, digits='Product Price')
    part_picking_id = fields.Many2one('stock.move','Part transfer')
    part_picking_state = fields.Selection(related='part_picking_id.state', string='Transfer')
    scrap_mode_on = fields.Boolean('Scrap mode')
    is_scrapped = fields.Boolean('Scrapped')
    hide_scrap_option = fields.Boolean('Hide Scrap Button (Technical)', compute='_get_scrap_state', store=False)

    @api.depends('scrap_mode_on', 'is_scrapped')
    def _get_scrap_state(self):
        # attrs = {'invisible' [()]} with an OR statement did not work, consolidating into a single flag boolean
        for rl in self:
            rl.hide_scrap_option = False if rl.scrap_mode_on and not rl.is_scrapped else True

    def scrap_product(self):
        for rl in self:
            repair_location_id, vbz_location_id, production_location_id, scrap_location_id = rl.repair_id._get_locations()
            stock_scrap = rl.env['stock.scrap'].create({
                'product_id': rl.product_id.id,
                'scrap_qty': 1,
                'product_uom_id': rl.product_id.uom_id.id,
                'lot_id': rl.lot_id.id,
                'location_id': rl.location_dest_id.id,
                'scrap_location_id': scrap_location_id.id,
                'origin': rl.name,
            })
            stock_scrap.do_scrap()
            if rl.product_uom_qty > 1:
                rl.product_uom_qty -= 1
            else:
                rl.product_uom_qty -= 1
                rl.write({'is_scrapped': True})

class UminaRepair(models.Model):
    _inherit = 'repair.order'

    fault_type_id = fields.Many2one('fault.type','Type of Fault')
    manufacturing_order_id = fields.Many2one('mrp.production','Manufacturing Order', readonly=True)
    post_repair_manufacturing_order_id = fields.Many2one('mrp.production','New Manufacturing Order', readonly=True)
    related_manufacturing_order_ids = fields.Many2many('mrp.production','Related Manufacturing Orders', compute='_get_related_manufacturing_orders', readonly=True, store=False)
    workorder_id = fields.Many2one('mrp.workorder','Workorder')
    
    location_src_id = fields.Many2one('stock.location', 'Last Workcenter Location', index=True, check_company=True, help="This is where the product came from and where it will be returned on successful repair")
    scraps_counter = fields.Integer('Scrap Count', compute='_get_move_and_scrap_count', store=False)
    moves_counter = fields.Integer('Moves Count', compute='_get_move_and_scrap_count', store=False)

    part_lot = fields.Char('Part Lot/Serial')
    part_lot_id = fields.Many2one('stock.production.lot', 'Part Lot/Serial Computed', check_company=True, compute='_compute_lot_object')
    part_product_id = fields.Many2one('product.product','Part Product', readonly=False, domain="[('id','in',part_product_domain_ids)]", store=True)
    part_product_ids = fields.Many2many('stock.quant','Part Products', compute='_compute_part_products', readonly=True)
    part_product_domain_ids = fields.Many2many('product.product','Part Products Domain', compute='_compute_part_products', readonly=True)
    part_product_uom = fields.Many2one(related='part_product_id.uom_id')
    part_product_qty = fields.Float('Part Quantity', default=1.0, digits='Product Unit of Measure')
    part_location_src_id = fields.Many2one('stock.location', 'Source location', index=True, check_company=True, help="This is the location where parts used to repair are located.")
    part_location_dest_id = fields.Many2one('stock.location', 'Destination location', index=True, check_company=True, help="This is the location where parts are used to repair.")
        
        # self.env['bus.bus']._sendone('mrp_production', 'workorder_update', self.id)

    def action_repair_move_lines(self):
        for repair in self:
            action = repair.env["ir.actions.actions"]._for_xml_id("um_mrp_repairs.action_repair_move_lines")
            action['domain'] = [('origin','=',repair.name),('location_dest_id.scrap_location','=',False)]
            return action

    def action_view_repair_scraps(self):
        for repair in self:
            action = repair.env["ir.actions.actions"]._for_xml_id("um_mrp_repairs.action_view_repair_scraps_tree")
            action['domain'] = [('origin','=',repair.name)]
            return action

    @api.depends('operations')
    def _get_move_and_scrap_count(self):
        for repair in self:
            repair.scraps_counter = repair.env['stock.scrap'].search_count([('origin','=',repair.name)])
            repair.moves_counter = repair.env['stock.move.line'].search_count([('origin','=',repair.name),('location_dest_id.scrap_location','=',False)])

    @api.depends('manufacturing_order_id')
    def _get_related_manufacturing_orders(self):
        for repair in self:
            if repair.manufacturing_order_id:
                repair.related_manufacturing_order_ids = False
                production_ids = repair.env['mrp.production']
                current_production_ids = repair.manufacturing_order_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids
                production_ids += current_production_ids

                while production_ids.filtered(lambda x: x.state not in ['done', 'cancel']):
                    production_ids += production_ids[0].procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids
                    if production_ids[0].product_qty > 1:
                        repair.related_manufacturing_order_ids = [(4,production_ids[0].id)]
                    production_ids -= production_ids[0]
            else:
                repair.related_manufacturing_order_ids = False


    def _get_locations(self):
        for repair in self:
            repair_location_id = repair.location_id
            vbz_location_id = repair.manufacturing_order_id.location_src_id
            production_location_id = repair.location_src_id
            scrap_location_id = repair.env['stock.location'].search([('scrap_location','=',True)],limit=1)
        return repair_location_id, vbz_location_id, production_location_id, scrap_location_id

    def _get_repair_line_and_move_vals(self, 
            repair_line_vals=False, 
            move_vals=False, 
            product_id=False, 
            lot_id=False, 
            product_uom_qty=1, 
            product_uom_qty_lines=1, 
            qty_done=1, 
            qty_done_lines=1, 
            location_src_id=False, 
            location_dest_id=False, 
            origin=False):
        """
        This function will generate values for 
            1) creation of repair.line values,
            2) creation of product move,
            3) creation of scrap move
        
        It is not intended to execute any of the actions.
        """
        for repair in self:
            repair_location_id, vbz_location_id, production_location_id, scrap_location_id = repair._get_locations()
            if move_vals:
                move_line_vals = {
                        'product_id': product_id.id,
                        'lot_id': lot_id.id if lot_id else False,
                        'product_uom_qty': product_uom_qty,
                        'product_uom_id': product_id.uom_id.id,
                        'qty_done': qty_done,
                        'package_id': False,
                        'result_package_id': False,
                        'company_id': repair.company_id.id,
                        'location_id': location_src_id.id,
                        'location_dest_id': location_dest_id.id,
                        'origin': repair.name
                        }
                stock_move = {
                        'name': origin,
                        'product_id': product_id.id,
                        'product_uom': product_id.uom_id.id,
                        'product_uom_qty': product_uom_qty,
                        'should_consume_qty': 0,
                        'partner_id': False,
                        'origin': repair.name,
                        'company_id': repair.company_id.id,
                        'repair_id': repair.id,
                        'location_id': location_src_id.id,
                        'location_dest_id': location_dest_id.id,
                        'move_line_ids': [(0,0,move_line_vals)]
                    }
            if repair_line_vals:
                repair_line_vals = {
                    'currency_id': repair.currency_id.id if repair.currency_id else repair.env.company.currency_id.id,
                    'company_id': repair.company_id.id if repair.company_id else repair.env.company.id,
                    'name': origin,
                    'type': 'add',
                    'lot_id': lot_id.id,
                    'product_id': product_id.id,
                    'product_uom': product_id.uom_id.id,
                    'product_uom_qty': product_uom_qty,
                    'repair_id': repair.id,
                    'location_id': location_src_id.id,
                    'location_dest_id': location_dest_id.id,
                }
            if repair_line_vals and move_vals:
                return repair_line_vals, stock_move
            elif repair_line_vals:
                return repair_line_vals
            elif move_vals:
                return stock_move

    @api.depends('part_lot', 'part_location_src_id')
    def _compute_part_products(self):
        for repair in self:
            quant_records = repair.env['stock.quant'].search([
                ('lot_id.name','=',repair.part_lot),
                ('location_id','=',repair.part_location_src_id.id)
                ])

            repair.part_product_ids = [(6,0,quant_records.ids)] if repair.part_lot else False
            repair.part_product_domain_ids = [(6,0,quant_records.mapped('product_id').ids)] if repair.part_lot else False
            repair.part_product_id = quant_records.product_id.id if len(quant_records) == 1 else repair.part_product_id
    
    @api.depends('part_lot','part_product_id')
    def _compute_lot_object(self):
        for repair in self:
            lot_object = repair.env['stock.production.lot'].search([('name','=',repair.part_lot),('product_id','=',repair.part_product_id.id)],limit=1)
            repair.part_lot_id =  lot_object.id if repair.part_product_id and repair.part_lot else False

    def action_done_and_next(self):
        for repair in self:
            action = repair.env["ir.actions.actions"]._for_xml_id("repair.action_repair_order_tree")
            repair_ids = repair.env['repair.order'].search([]).filtered(lambda x: x.state not in ['done', 'cancel'])
            if len(repair_ids) == 1:
                action.update({
                    'view_mode': 'form',
                    'res_id': repair_ids.id,
                    'views': [(False, 'form')],
                })
            else:
                action.update({
                    'view_mode': 'kanban, form',
                    'views': [(False, 'kanban'), (False, 'form')],
                    'context': {'group_by': ['state']}
                })
            return action
    
    def action_add_part(self):
        for repair in self:
            repair.write({
                'part_location_src_id': repair.env.ref('um_mrp_data.work_location_2').id if not repair.part_location_src_id else repair.part_location_src_id,
                # 'part_location_src_id': repair.env.ref('um_mrp_data.stock_location_partner_production_gamyba').id if not repair.part_location_src_id else repair.part_location_src_id,
                'part_location_dest_id': repair.location_id.id if repair.location_id else False,
            })
            repair.operations.write({'scrap_mode_on':False})
            # default_<param> context did not work, using repair.write() instead.
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'repair.order',
                'views': [[repair.env.ref('um_mrp_repairs.repair_add_part_popup').id, 'form']],
                'res_id': repair.id,
                'target': 'new',
                'context': {'form_view_initial_mode': 'edit'}
            }
    
    def add_repair_line(self):
        for repair in self:

            repair_location_id, vbz_location_id, production_location_id, scrap_location_id = repair._get_locations()
            repair_line_vals, stock_move_vals = repair._get_repair_line_and_move_vals(
                repair_line_vals=True,
                move_vals=True,
                product_id=repair.part_product_id,
                lot_id=repair.part_lot_id,
                product_uom_qty=repair.part_product_qty,
                qty_done=repair.part_product_qty,
                location_src_id=repair.part_location_src_id,
                location_dest_id=repair.part_location_dest_id,
                origin=repair.name
            )
            repair_line = repair.env['repair.line'].create(repair_line_vals)
            stock_move = repair.env['stock.move'].create(stock_move_vals)
            quant = repair.env['stock.quant']

            available_qty = quant._get_available_quantity(
                product_id=repair.part_product_id, 
                location_id=repair.part_location_src_id, 
                lot_id=repair.part_lot_id)

            if repair.part_product_qty > available_qty:
                unreserve_qty = -(repair.part_product_qty - available_qty)

                quant._update_reserved_quantity(
                product_id=repair.part_product_id, 
                location_id=repair.part_location_src_id, 
                quantity=unreserve_qty, 
                lot_id=repair.part_lot_id)

            quant._update_reserved_quantity(
                product_id=repair.part_product_id, 
                location_id=repair.part_location_src_id, 
                quantity=repair.part_product_qty, 
                lot_id=repair.part_lot_id)
            stock_move._action_confirm()
            stock_move._action_done()

            repair_line['part_picking_id'] = stock_move.id

            # Reset repair.order part fields to False/Null.
            self.write({
                'part_lot': False,
                'part_product_id': False,
                'part_product_qty': 1
            })

    def action_scrap(self):
        for repair in self:
            for line in repair.operations:
                line.write({'scrap_mode_on': False if line.scrap_mode_on and not line.is_scrapped else True})

    def action_scrap_all(self):
        for repair in self:
            repair_location_id, vbz_location_id, production_location_id, scrap_location_id = repair._get_locations()
            repair.workorder_id.discount_source_qty()
            stock_scrap = repair.env['stock.scrap'].create({
                'product_id': repair.product_id.id,
                'scrap_qty': 1,
                'product_uom_id': repair.product_id.uom_id.id,
                'lot_id': repair.lot_id.id,
                'location_id': repair_location_id.id,
                'scrap_location_id': scrap_location_id.id,
                'origin': repair.name,
            })
            stock_scrap.do_scrap()
            for rl in repair.operations:
                while rl.product_uom_qty:
                    rl.scrap_product()
            repair.write({'state':'done'})
            repair.operations.write({'scrap_mode_on':False})

    
    def action_select_type_of_fault(self):
        for repair in self:
            action = repair.env["ir.actions.actions"]._for_xml_id("um_mrp_repairs.action_type_of_fault")
            action['res_id'] = repair.id
            return action

    def action_select_type_of_fault_scrap_all(self):
        for repair in self:
            action = repair.env["ir.actions.actions"]._for_xml_id("um_mrp_repairs.action_type_of_fault_scrap_all")
            action['res_id'] = repair.id
            return action
    
    def action_repair_end(self):
        for repair in self:
            if repair.manufacturing_order_id:
                repair_location_id, vbz_location_id, production_location_id, scrap_location_id = repair._get_locations()
                # Move all parts used for repairing
                for repair_line in repair.operations:
                    if not repair_line.is_scrapped:
                        move_vals = repair._get_repair_line_and_move_vals(
                            move_vals=True,
                            product_id=repair_line.product_id,
                            lot_id=repair_line.lot_id,
                            product_uom_qty=repair_line.product_uom_qty,
                            qty_done=repair_line.product_uom_qty,
                            location_src_id=repair_line.location_dest_id,
                            location_dest_id=repair.location_src_id,
                            origin=repair.name
                        )
                        move_id = repair.env['stock.move'].create(move_vals)
                        move_id.write({'raw_material_production_id': repair.manufacturing_order_id.id})

                        quant = repair.env['stock.quant']
                        quant._update_reserved_quantity(
                            product_id=repair_line.product_id, 
                            location_id=repair_line.location_dest_id, 
                            quantity=repair_line.product_uom_qty, 
                            lot_id=repair_line.lot_id)


                        # To see these parts in a traceability report, we need to find stock.move.line where our final product was produced
                        produce_line_ids = repair.manufacturing_order_id.finished_move_line_ids.filtered(lambda f: f.product_id.id == repair.manufacturing_order_id.product_id.id)
                        
                        part_move_line = move_id.mapped('move_line_ids')
                        # We know for a fact that move_id.move_line_ids contains exactly one item - the one that we created
                        produce_line_ids.write({'consume_line_ids': [(4, part_move_line.id)]})

                        move_id._action_confirm()
                        move_id._action_done()

                        stock_scrap = repair.env['stock.scrap'].create({
                            'product_id': repair_line.product_id.id,
                            'scrap_qty': repair_line.product_uom_qty,
                            'product_uom_id': repair_line.product_id.uom_id.id,
                            'lot_id': repair_line.lot_id.id,
                            'location_id': repair.location_src_id.id,
                            'scrap_location_id': scrap_location_id.id,
                            'origin': repair.name
                        })
                        stock_scrap.do_scrap()

            # Move final product twice: first from repair location to VBZ, then from VBZ to production location
            move_vals = repair._get_repair_line_and_move_vals(
                        move_vals=True,
                        product_id=repair.product_id,
                        lot_id=repair.lot_id,
                        location_src_id=repair_location_id,
                        location_dest_id=vbz_location_id,
                        origin=repair.name
                    )
            move_id = repair.env['stock.move'].create(move_vals)
            quant = repair.env['stock.quant']
            quant._update_reserved_quantity(
                product_id=repair.product_id, 
                location_id=repair_location_id, 
                quantity=1, 
                lot_id=repair.lot_id)
            move_id._action_confirm()
            move_id._action_done()
            
            move_vals = repair._get_repair_line_and_move_vals(
                        move_vals=True,
                        product_id=repair.product_id,
                        lot_id=repair.lot_id,
                        location_src_id=vbz_location_id,
                        location_dest_id=production_location_id,
                        origin=repair.name
                    )
            move_id = repair.env['stock.move'].create(move_vals)
            quant = repair.env['stock.quant']
            quant._update_reserved_quantity(
                product_id=repair.product_id, 
                location_id=vbz_location_id, 
                quantity=1, 
                lot_id=repair.lot_id)
            move_id._action_confirm()
            move_id._action_done()

            #Split MO, and instantly set new_production_order variable as 
            #new production order 
            amount = 1
            amounts = {self.manufacturing_order_id: [amount, amount]}
            new_production_order = self.manufacturing_order_id._split_productions(amounts)[1]

            test_type_passfail = self.env.ref('quality_control.test_type_passfail')

            #Unlink all checks that are not pass/fail, because after returning from repair
            #we need only one quality check pass/fail.
            quality_checks_not_pass_fail = new_production_order.workorder_ids.check_ids.filtered(lambda x: x.test_type_id != test_type_passfail.id)
            quality_checks_not_pass_fail.unlink()

            # On successful repair, we need to return product to manufacturing for another QA check (Pass/Fail).
            # for old_production_order in self.manufacturing_order_id:
            new_production_order.update({
                'bom_id': False,
                'move_raw_ids': False,
                'lot_producing_id': repair.lot_id.id,
                # 'backorder_sequence': 1,
                'needs_repairing': False,
                'has_returned_from_repair': True,
                'pre_repair_manufacturing_order_id': self.manufacturing_order_id.id,
                'qty_producing': amount,
            })
            moves=repair.env['stock.move']

            #Traceability <- very important
            repair_service_product = self.env.ref('um_mrp_data.repair_service')
            for manufacturing_order in [self.manufacturing_order_id, new_production_order]:
                # To see repair_service_product in a traceability report, 
                # we need to find stock.move.line where our final product was produced
                # and add a stock.move.line record with repair_service_product into 'consume_line_ids'
                produce_line_ids = manufacturing_order.finished_move_line_ids.filtered(lambda f: f.product_id.id == repair.product_id.id)
                # Check if such consume_line_id exists, if so, just update quantity with +=1
                if repair_service_product.id in produce_line_ids.consume_line_ids.mapped('product_id').ids:
                    line_with_repair_product = produce_line_ids.consume_line_ids.filtered(lambda c: c.product_id.id == repair_service_product.id)
                    line_with_repair_product[0].write({'qty_done': line_with_repair_product[0].qty_done + 1})
                # If not, create stock.move, stock.move.line and add it to consume_line_ids of produce_line_ids
                else:
                    move_vals = repair._get_repair_line_and_move_vals(
                        move_vals=True,
                        product_id=repair_service_product,
                        qty_done=1,
                        lot_id=False,
                        location_src_id=repair_location_id,
                        location_dest_id=vbz_location_id,
                        origin=repair.name
                    )
                    move_id = repair.env['stock.move'].create(move_vals)
                    move_id.write({'raw_material_production_id': manufacturing_order.id})
                    # We know for a fact that move_id.move_line_ids contains exactly one item - the one that we created
                    part_move_line = move_id.mapped('move_line_ids')
                    produce_line_ids.write({'consume_line_ids': [(4, part_move_line.id)]})
                    # There is no need to _action_confirm()/_action_done() this stock move, because it contains only one consumable object.
                    # Regardless if the product passes or fails next QA Check-point, we will delete associated manufacturing project
                    # And this stock move gets cancelled automatically.
                    # We could _action_confirm()/_action_done() but it's excessive and opens up a risk for an UserError.

            # new_production_order.action_confirm()

            repair.write({'state':'done'})
            repair.operations.write({'scrap_mode_on':False})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        # We don't really need this - Umina
        for order in self:
            if order.invoice_id and order.invoice_id.posted_before:
                pass
                # raise UserError(_('You can not delete a repair order which is linked to an invoice which has been posted once.'))
            if order.state not in ('draft', 'cancel'):
                pass
                # raise UserError(_('You can not delete a repair order once it has been confirmed. You must first cancel it.'))

class UminaQualityWizard(models.TransientModel):
    _inherit = 'quality.check.wizard'
    
    def button_repair(self):
        """
        On click of 'Repair request', we mark manufacturing order as 'needs repairing'.

        The following four conditions are checked in _check_repairing() method:
            -If product has not been repaired before and does not need repairing:
                -Proceed business as usual (do nothing)
            -If product has not been repaired before but it needs repairing:
                -Move final product away from virtual buffer zone so it would not get reserved and could not be consumed
                -The final product is moved to repair location (there's a flag-boolean in stock.location)
                -Create a repair.order record
            -If product has been repaired before but it needs repairing again:
                -Delete this dummy manufacturing order
                -Create a repair.order record
            -If product has been repaired before but does not need repairing anymore:
                -Delete this dummy manufacturing order
                -Move final product back to the virtual buffer zone where it gets immediately reserved
        The four conditions allow endless looping (unlimited number of repairing orders and quality checks for a single final product)
        """
        # Please note: self.workorder_id.production_id is not the same as
        # (XML context="{'production_id': production_id}"). This might be due to
        # complicated Odoo backorders system
        production_id = self.env['mrp.production'].browse(self.env.context.get('production_id'))
        production_id.write({'needs_repairing': True})
        # 'needs_repairing': False  is important because it allows
        # user going back to Pass/Fail check and re-selecting option
        production_id.write({'to_be_scrapped': False})
        production_id.lot_producing_id.produced_class = False
        if production_id.has_returned_from_repair:
            if not production_id._check_repairing():
                production_id.unlink()
                return self.env['mrp.workorder'].um_mrp_workorder_todo()


    def button_scrap(self):
        """
        On click of 'Scrap all':
            - (1) The final good needs to be scrapped
            - (2) All source (upper-level) manufacturing orders need to have their quantity to produce lowered by 1
        
        If manufacturing order is a dummy:
            - Then the order needs to be deleted
            - We perform (2) action on original manufacturing order
        """
        # Please note: self.workorder_id.production_id is not the same as
        # (XML context="{'production_id': production_id}"). This might be due to
        # complicated Odoo backorders system
        production_id = self.env['mrp.production'].browse(self.env.context.get('production_id'))
        # 'needs_repairing': False  is important because it allows
        # user going back to Pass/Fail check and re-selecting option
        production_id.write({'needs_repairing': False})
        production_id.write({'to_be_scrapped': True})
        production_id.lot_producing_id.produced_class = False
        if production_id.has_returned_from_repair:
            if not production_id._check_repairing():
                production_id.unlink()
                return self.env['mrp.workorder'].um_mrp_workorder_todo()

