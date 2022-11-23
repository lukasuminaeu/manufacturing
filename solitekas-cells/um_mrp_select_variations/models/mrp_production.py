from odoo import models, fields, api
from odoo.exceptions import UserError

from odoo import models, fields, api


class UminaRepair(models.Model):
    _inherit = 'mrp.production'

    is_any_child_production_order_started = fields.Boolean(
        'Has the order been started', compute='get_child_production_states', store=False)
        
    child_production_ids = fields.Many2many(
        'mrp.production', 'parent_child_manufaturing_rel', 'parent_id', 'child_id', string='Child Manufacturing Orders', readonly=True)
        # 'mrp.production', 'parent_child_manufaturing_rel', 'parent_id', 'child_id', string='Child Manufacturing Orders', readonly=True, compute='get_child_production_ids', store=True)
    
    main_production_id = fields.Many2one('mrp.production')

    # main_production_id = fields.Many2one('mrp.production', compute='compute_main_production_id')
    current_variation_id = fields.Many2one(
        'product.product', 'Current Variation', readonly=True, copy=True)
    new_variation_id = fields.Many2one(
        'product.product', 'Select Variation', domain="[('id', 'in', new_variation_domain_ids)]")
    new_variation_domain_ids = fields.Many2many(related='bom_id.variants_ids')
    active_variation_rules = fields.Many2many(
        comodel_name='mrp.production.variation.rules', string='Variation Rules', compute='_get_variation_rules')
    varying_production_lines = fields.Many2many('stock.move', 'mrp_production_variant_move_line_rel', 'production_id', 'move_id', string='Varying Lines',
                                                help='These lines will be changed if different variation is selected.')

    # def compute_main_production_id(self):
    #     """Get final production id for any child production id"""
    #     for production in self:
    #         production.main_production_id = False
    #         source_mo = production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids - production
    #         main_production_id = False
    #         if source_mo:
    #             source_mo = min(source_mo)

    #             source_mos = source_mo

    #             main_production_id = False
    #             index = 0
    #             while source_mos:
    #                 if index < len(source_mos):
    #                     source_mo_of_source_mo = source_mos[index].procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids - source_mos[index]
    #                     index += 1
    #                     source_mos += source_mo_of_source_mo
    #                 else:
    #                     main_production_id = source_mos[index - 1]
    #                     break
    #             return main_production_id


    @api.onchange('new_variation_id')
    def _prompt_error_if_started(self):
        for production in self:
            if production.is_any_child_production_order_started:
                raise UserError(
                    'Manufacturing Order has already been started!')

    @api.onchange('new_variation_id')
    def _get_variation_rules(self):
        for production in self:
            production.active_variation_rules = production.bom_id.variation_rules_ids.filtered(
                lambda p: p.product_id.id == production.new_variation_id.id and p.active_variation_rule)

    def select_variation(self):
        """
        This is the main function behind applying variation rules.
        The goal of this function is three-fold:
            1) Change all raw materials of all child production orders
            according to the variation rules that are configured in mrp.bom
            2) Change all picking moves (if there is a picking) of all
            child production orders according to the variation rules that
            are configured in mrp.bom
            3) Change original production order product_id to new_variation_id
            so that when we record_production(), then we produce a variant
            instead of the original product
        """
        self.ensure_one()
        variation_obj = self.env['mrp.production.variation.rules']
        production_original = self
        product_original = self.product_id
        production_ids = self + self.child_production_ids   # This should take all the bottom lines

        # Reset raw material lines in original production order
        production_original.write({'varying_production_lines': [(5, 0)]})

        if production_original.new_variation_id == production_original.current_variation_id:
            raise UserError(
                'Please select variation that differs from the current variation!')

        # Goal 3: Set current_variation_id and product_id as new_variation_id
        # and replace any existing stock.move product_id with new_variation_id
        # Note: we do not need to iterate through stock.move.line because that
        # is taken care of by standard features (quality_mrp.models.write() function)
        production_original.write({
            'current_variation_id': production_original.new_variation_id,
            'product_id': production_original.new_variation_id
            })
        for move in production_original.move_finished_ids.filtered(lambda move: move.product_id == product_original):
            move.update({
                'product_id': production_original.new_variation_id
            })

        # Goal 1 and 2: for original production order and for every child production order
        # We want to find associated stock.picking (link is 'origin', see um_transfers_bz.models.procure_components())
        # and replace every stock.move / stock.move.line that has not been started or cancelled yet
        # according to the variation rules configured in mrp.bom
        # On every call of select_variation() we first restore original values
        # to allow searching for variation_line. This allows selecting variation inf. amount of times.
        for production in production_ids:
            picking_id = production.env['stock.picking'].search([('origin','=',production.name), ('state', 'in', ['draft', 'confirmed', 'assigned', 'waiting'])], limit=1)
            # Change move raw ids
            for move in production.move_raw_ids:
                # Restore original product to allow variation_line search below
                move.product_id = move.original_product if move.original_product else move.product_id
                move.product_uom_qty = move.original_product_uom_qty if move.original_product_uom_qty else move.product_uom_qty

                variation_line = variation_obj.search([('component_before_id', '=', move.product_id.id),
                                                       ('component_bom_id', '=', production.bom_id.id),
                                                       ('bom_id','=',production_original.bom_id.id),
                                                       ('product_id', '=', production_original.new_variation_id.id),
                                                       ('replace_or_new', '=', 'replace')], limit=1)

                # We first apply variation rule if component differs, then we will apply
                # variation rules if quantities differ (i.e. one variation might require 1 piece of
                # glass and another variation might require 2 pcs of glass)
                if variation_line and variation_line.component_before_id != variation_line.component_after_id:
                    
                    # Replace raw materials
                    if not move.original_product:
                        move.original_product = move.product_id
                    move.product_id = variation_line.component_after_id

                    # Restore original product to allow picking_move search below
                    picking_move_to_restore = picking_id.move_lines.filtered(lambda x: x.original_product == variation_line.component_before_id)
                    if picking_move_to_restore:
                        picking_move_to_restore.write({
                            'product_id': picking_move_to_restore.original_product.id,
                            'product_uom_qty': picking_move_to_restore.original_product_uom_qty if picking_move_to_restore.original_product_uom_qty else picking_move_to_restore.product_uom_qty,
                        })

                    # Search for picking move lines that should be replaced
                    picking_move = picking_id.move_lines.filtered(lambda x: x.product_id == variation_line.component_before_id)

                    if picking_move:
                        # Replace picking moves
                        picking_move.write({
                            'original_product': variation_line.component_before_id,
                            'product_id': variation_line.component_after_id.id
                        })
                        picking_move.move_line_ids.unlink()
                        picking_move._prepare_move_line_vals(quantity=picking_move.product_uom_qty)


                # Here we apply variation rule for different quantities
                if variation_line and variation_line.product_qty_before != variation_line.product_qty_after:

                    # Replace raw materials
                    if not move.original_product_uom_qty:
                        move.original_product_uom_qty = move.product_uom_qty
                    multiplier_qty = variation_line.product_qty_before and variation_line.product_qty_after / variation_line.product_qty_before or 1.0
                    move.product_uom_qty = move.product_uom_qty * multiplier_qty

                    # Search for picking move lines that should be replaced
                    picking_move = picking_id.move_lines.filtered(lambda x: x.product_id == variation_line.component_before_id)
                    
                    if picking_move:
                        # Replace picking moves
                        picking_move.write({
                            'original_product_uom_qty': picking_move.product_uom_qty,
                            'product_uom_qty': move.product_uom_qty
                        })
                        for ml in picking_move.move_line_ids:
                            ml.qty_done = ml.qty_done * multiplier_qty

                # If we apply any of the variation rules, then add it to the production order M2M field.
                if variation_line and (variation_line.component_before_id != variation_line.component_after_id or variation_line.product_qty_before != variation_line.product_qty_after):
                    production_original.write({'varying_production_lines': [(4, move.id)]})

    def unlink(self):
        for record in self:
            if not self.env.context.get('unlink_only') and not record.has_returned_from_repair:
                move_ids = self.env['stock.move']
                move_ids += record.move_raw_ids
                move_ids += record.move_finished_ids
                picking_id = self.env['stock.picking'].search([('origin', '=', record.name)])
                picking_id.action_cancel()
                picking_id.unlink()
                all_canceled = all([order.state == 'cancel' for order in record.child_production_ids])
                if not record.child_production_ids.filtered(lambda c: c.state not in ['draft', 'confirmed']) or all_canceled:
                    for c in record.child_production_ids:
                        move_ids += c.move_raw_ids
                        move_ids += c.move_finished_ids

                        picking_id = self.env['stock.picking'].search([('origin', '=', c.name)])
                        picking_id.action_cancel()
                        picking_id.unlink()
                    record.child_production_ids.with_context(unlink_only=True).unlink()
                else:
                    raise UserError('At least one child manufacturing order has been started!')
                move_ids._action_cancel()
                move_ids.unlink()
        return super(UminaRepair, self).unlink()

    def loop_for_child_production_ids(self):
        for record in self:
            sources = record.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids
            return_mos = record.env['mrp.production']
            index = 0
            while True:
                src_src = sources[index].procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids
                if src_src:
                    for src1 in src_src:
                        if src1 not in sources:
                            sources += src1
                    index += 1
                else:
                    break

            sources += record
            return sources

    # @api.depends('procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids')
    # @api.depends('procurement_group_id.mrp_production_ids', 'procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids')
    def get_child_production_ids(self):
        for production in self:
            # if not production.child_production_ids:
            #     production.child_production_ids = False
            # production.child_production_ids = False
            production_ids = production.env['mrp.production']
            child_production_ids = production.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids - production

            production_ids += child_production_ids
            if child_production_ids:
                for child_prod in child_production_ids:
                    production.child_production_ids += child_prod[0]

                    if production.main_production_id:
                        production.main_production_id.child_production_ids += child_prod[0]

                source_mo = production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids - production
                if len(source_mo) > 1:
                    source_mo = min(source_mo)

                if source_mo and source_mo.product_id.is_final_product:
                    production.main_production_id = source_mo
                    if production.main_production_id != source_mo:
                        production.main_production_id.child_production_ids += source_mo

                    all_childs = production.loop_for_child_production_ids()
                    for child in all_childs:
                        source_mo.child_production_ids += child
                        child.main_production_id = source_mo.id
                        child.main_production_id.child_production_ids += child

    @api.depends('procurement_group_id')
    def get_child_production_states(self):
        for production in self:
            production.is_any_child_production_order_started = True if production.child_production_ids.filtered(
                lambda c: c.state not in ['draft', 'confirmed']) else False
    
    def set_current_variation(self):
        for production in self + self.child_production_ids:
            production.current_variation_id = production.product_id




