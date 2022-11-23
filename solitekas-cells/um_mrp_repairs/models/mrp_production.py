from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.tools.misc import OrderedSet, format_date, groupby as tools_groupby
from collections import defaultdict
from odoo.tools import float_compare, is_html_empty
from odoo.tools.float_utils import float_is_zero

class UminaRepair(models.Model):
    _inherit = 'mrp.production'

    repaired_ids = fields.One2many('repair.order','manufacturing_order_id','Related repaired MOs')
    needs_repairing = fields.Boolean('Is waiting for repair done', copy=False)
    to_be_scrapped = fields.Boolean('Is waiting to be scrapped', copy=False)
    has_returned_from_repair = fields.Boolean('Has returned from repair', copy=False)
    pre_repair_manufacturing_order_id = fields.Many2one('mrp.production','Pre-Repair Manufacturing Order')


    def _split_productions(self, amounts=False, cancel_remaning_qty=False, set_consumed_qty=False):
        """ Splits productions into productions smaller quantities to produce, i.e. creates
        its backorders.
        :param dict amounts: a dict with a production as key and a list value containing
        the amounts each production split should produce including the original production,
        e.g. {mrp.production(1,): [3, 2]} will result in mrp.production(1,) having a product_qty=3
        and a new backorder with product_qty=2.
        :return: mrp.production records in order of [orig_prod_1, backorder_prod_1,
        backorder_prod_2, orig_prod_2, backorder_prod_2, etc.]
        """
        def _default_amounts(production):
            return [production.qty_producing, production._get_quantity_to_backorder()]

        if not amounts:
            amounts = {}
        for production in self:
            mo_amounts = amounts.get(production)
            if not mo_amounts:
                amounts[production] = _default_amounts(production)
                continue
            total_amount = sum(mo_amounts)
            if total_amount < production.product_qty and not cancel_remaning_qty:
                amounts[production].append(production.product_qty - total_amount)
            
            #Umina edit: we dont need this error here, because we want to be able to split
            #MO even if its current producing quanntity is 0.
            
            # elif total_amount > production.product_qty or production.state in ['done', 'cancel']:
            #     raise UserError(_("Unable to split with more than the quantity to produce."))

        backorder_vals_list = []
        initial_qty_by_production = {}

        # Create the backorders.
        for production in self:
            initial_qty_by_production[production] = production.product_qty
            if production.backorder_sequence == 0:  # Activate backorder naming
                production.backorder_sequence = 1
            production.name = self._get_name_backorder(production.name, production.backorder_sequence)
            production.product_qty = amounts[production][0]
            backorder_vals = production.copy_data(default=production._get_backorder_mo_vals())[0]
            backorder_qtys = amounts[production][1:]

            next_seq = max(production.procurement_group_id.mrp_production_ids.mapped("backorder_sequence"), default=1)

            for qty_to_backorder in backorder_qtys:
                next_seq += 1
                backorder_vals_list.append(dict(
                    backorder_vals,
                    product_qty=qty_to_backorder,
                    name=production._get_name_backorder(production.name, next_seq),
                    backorder_sequence=next_seq,
                    state='confirmed'
                ))

        backorders = self.env['mrp.production'].with_context(skip_confirm=True).create(backorder_vals_list)

        index = 0
        production_to_backorders = {}
        production_ids = OrderedSet()
        for production in self:
            number_of_backorder_created = len(amounts.get(production, _default_amounts(production))) - 1
            production_backorders = backorders[index:index + number_of_backorder_created]
            production_to_backorders[production] = production_backorders
            production_ids.update(production.ids)
            production_ids.update(production_backorders.ids)
            index += number_of_backorder_created

        # Split the `stock.move` among new backorders.
        new_moves_vals = []
        moves = []
        for production in self:
            for move in production.move_raw_ids | production.move_finished_ids:
                if move.additional:
                    continue
                unit_factor = move.product_uom_qty / initial_qty_by_production[production]
                initial_move_vals = move.copy_data(move._get_backorder_move_vals())[0]
                move.with_context(do_not_unreserve=True).product_uom_qty = production.product_qty * unit_factor

                for backorder in production_to_backorders[production]:
                    move_vals = dict(
                        initial_move_vals,
                        product_uom_qty=backorder.product_qty * unit_factor
                    )
                    if move.raw_material_production_id:
                        move_vals['raw_material_production_id'] = backorder.id
                    else:
                        move_vals['production_id'] = backorder.id
                    new_moves_vals.append(move_vals)
                    moves.append(move)

        backorder_moves = self.env['stock.move'].create(new_moves_vals)
        # Split `stock.move.line`s. 2 options for this:
        # - do_unreserve -> action_assign
        # - Split the reserved amounts manually
        # The first option would be easier to maintain since it's less code
        # However it could be slower (due to `stock.quant` update) and could
        # create inconsistencies in mass production if a new lot higher in a
        # FIFO strategy arrives between the reservation and the backorder creation
        move_to_backorder_moves = defaultdict(lambda: self.env['stock.move'])
        for move, backorder_move in zip(moves, backorder_moves):
            move_to_backorder_moves[move] |= backorder_move

        move_lines_vals = []
        assigned_moves = set()
        partially_assigned_moves = set()
        move_lines_to_unlink = set()

        for initial_move, backorder_moves in move_to_backorder_moves.items():
            ml_by_move = []
            product_uom = initial_move.product_id.uom_id
            for move_line in initial_move.move_line_ids:
                available_qty = move_line.product_uom_id._compute_quantity(move_line.product_uom_qty, product_uom)
                if float_compare(available_qty, 0, precision_rounding=move_line.product_uom_id.rounding) <= 0:
                    continue
                ml_by_move.append((available_qty, move_line, move_line.copy_data()[0]))

            initial_move.move_line_ids.with_context(bypass_reservation_update=True).write({'product_uom_qty': 0})
            moves = list(initial_move | backorder_moves)

            move = moves and moves.pop(0)
            move_qty_to_reserve = move.product_qty
            for quantity, move_line, ml_vals in ml_by_move:
                while float_compare(quantity, 0, precision_rounding=product_uom.rounding) > 0 and move:
                    # Do not create `stock.move.line` if there is no initial demand on `stock.move`
                    taken_qty = min(move_qty_to_reserve, quantity)
                    taken_qty_uom = product_uom._compute_quantity(taken_qty, move_line.product_uom_id)
                    if move == initial_move:
                        move_line.with_context(bypass_reservation_update=True).product_uom_qty = taken_qty_uom
                        if set_consumed_qty:
                            move_line.qty_done = taken_qty_uom
                    elif not float_is_zero(taken_qty_uom, precision_rounding=move_line.product_uom_id.rounding):
                        new_ml_vals = dict(
                            ml_vals,
                            product_uom_qty=taken_qty_uom,
                            move_id=move.id
                        )
                        if set_consumed_qty:
                            new_ml_vals['qty_done'] = taken_qty_uom
                        move_lines_vals.append(new_ml_vals)
                    quantity -= taken_qty
                    move_qty_to_reserve -= taken_qty

                    if float_compare(move_qty_to_reserve, 0, precision_rounding=move.product_uom.rounding) <= 0:
                        assigned_moves.add(move.id)
                        move = moves and moves.pop(0)
                        move_qty_to_reserve = move and move.product_qty or 0

                # Unreserve the quantity removed from initial `stock.move.line` and
                # not assigned to a move anymore. In case of a split smaller than initial
                # quantity and fully reserved
                if quantity:
                    self.env['stock.quant']._update_reserved_quantity(
                        move_line.product_id, move_line.location_id, -quantity,
                        lot_id=move_line.lot_id, package_id=move_line.package_id,
                        owner_id=move_line.owner_id, strict=True)

            if move and move_qty_to_reserve != move.product_qty:
                partially_assigned_moves.add(move.id)

            move_lines_to_unlink.update(initial_move.move_line_ids.filtered(
                lambda ml: not ml.product_uom_qty and not ml.qty_done).ids)

        self.env['stock.move'].browse(assigned_moves).write({'state': 'assigned'})
        self.env['stock.move'].browse(partially_assigned_moves).write({'state': 'partially_available'})
        # Avoid triggering a useless _recompute_state
        self.env['stock.move.line'].browse(move_lines_to_unlink).write({'move_id': False})
        self.env['stock.move.line'].browse(move_lines_to_unlink).unlink()
        self.env['stock.move.line'].create(move_lines_vals)

        # We need to adapt `duration_expected` on both the original workorders and their
        # backordered workorders. To do that, we use the original `duration_expected` and the
        # ratio of the quantity produced and the quantity to produce.
        for production in self:
            initial_qty = initial_qty_by_production[production]
            initial_workorder_remaining_qty = []
            bo = production_to_backorders[production]

            # Adapt duration
            for workorder in (production | bo).workorder_ids:
                workorder.duration_expected = workorder.duration_expected * workorder.production_id.product_qty / initial_qty

            # Adapt quantities produced
            for workorder in production.workorder_ids:
                initial_workorder_remaining_qty.append(max(workorder.qty_produced - workorder.qty_production, 0))
                workorder.qty_produced = min(workorder.qty_produced, workorder.qty_production)
            workorders_len = len(bo.workorder_ids)
            for index, workorder in enumerate(bo.workorder_ids):
                remaining_qty = initial_workorder_remaining_qty[index // workorders_len]
                if remaining_qty:
                    workorder.qty_produced = max(workorder.qty_production, remaining_qty)
                    initial_workorder_remaining_qty[index % workorders_len] = max(remaining_qty - workorder.qty_produced, 0)
        backorders.workorder_ids._action_confirm()

        return self.env['mrp.production'].browse(production_ids)


    def _get_move_vals(self, needs_repairing=False, from_prod=False):
        """
        After repair, the product is pushed:
            Repair_location -> VBZ and
            VBZ -> Production_location
        CASE 1: If product still needs repairing, then it needs to be pushed:
            Production_location -> VBZ
            VBZ -> Repair_location
        CASE 2: If product no longer needs repairing, then it needs to be pushed:
            Production_location -> VBZ
        
        In CASE 1, this function will be called twice with (from_prod, not needs_repairing) and (not from_prod, needs_repairing)
        In CASE 2, this function will be called once with (from_prod, not needs_repairing)
        """
        for production_id in self:
            repairing_location = production_id.env['stock.location'].search([('is_repair_location','=',True)])
            virtual_buffer_zone_location = production_id.env['stock.location'].search([('is_stc_vbz','=',True)])
            if not repairing_location:
                raise UserError(_('Please check configuration: Manufacturing needs at least one location with check-box "Is Repair Location" checked!'))
            if not virtual_buffer_zone_location:
                raise UserError(_('Please check configuration: Manufacturing needs at least one location with check-box "Is STC VBZ" checked!'))
            production_location = production_id.product_id.property_stock_production

            # src_location_id = production_location if from_prod else virtual_buffer_zone_location
            src_location_id = production_location if from_prod else self.location_dest_id
            dest_location_id = repairing_location if needs_repairing else virtual_buffer_zone_location

            move_vals = {
                'name': f'Send {production_id.name} for repair',
                'product_id': production_id.product_id.id,
                'product_uom_qty': production_id.qty_producing,
                'product_uom': production_id.product_id.uom_id.id,
                'location_id': src_location_id.id,
                'location_dest_id': dest_location_id.id,
                'should_consume_qty': 0,
                # Setting production_id to False is very important because Odoo native code doesn't have limit=1 in one function and it raises singleton error
                'production_id': False, 
                'move_line_ids': [(0, 0, {
                    'product_id': production_id.product_id.id,
                    'lot_id': production_id.lot_producing_id.id,
                    'product_uom_qty': 0, 
                    'product_uom_id': production_id.product_id.uom_id.id,
                    'qty_done': production_id.qty_producing,
                    'package_id': False,
                    'result_package_id': False,
                    'location_id': src_location_id.id,
                    'location_dest_id': dest_location_id.id,})],
                    'company_id': production_id.company_id.id,
                'company_id': production_id.company_id.id,
                'origin': production_id.name}
            return move_vals

    def _get_repair_vals(self):
        for production_id in self:
            repairing_location = production_id.env['stock.location'].search([('is_repair_location','=',True)])
            if not repairing_location:
                raise UserError(_('Please check configuration: Manufacturing needs at least one location with check-box "Is Repair Location" checked!'))
            repair_order_vals = {
                        'manufacturing_order_id': production_id.pre_repair_manufacturing_order_id.id if production_id.pre_repair_manufacturing_order_id else production_id.id,
                        'description': f'Repair for {production_id.display_name} order, workcenter name: {production_id.env.user.display_name}',
                        'product_id': production_id.product_id.id,
                        'lot_id': production_id.lot_producing_id.id,
                        'product_qty': production_id.qty_producing,
                        'product_uom': production_id.product_id.uom_id.id,
                        'location_src_id': production_id.product_id.property_stock_production.id,
                        'location_id': repairing_location.id
                    }
        return repair_order_vals

    def discount_source_qty(self, discount_self=False):
        for production_id in self:
            production_ids = production_id.env['mrp.production']
            current_production_ids = production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids
            production_ids += current_production_ids

            # # Include self production too, if variable is set to 'True'
            # if discount_self:
            #     production_ids += production_id

            while production_ids.filtered(lambda x: x.state not in ['done', 'cancel', 'to_close']):
                production_ids += production_ids[0].procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids
                if production_ids[0].product_qty > 1:
                    change_qty = production_id.env['change.production.qty'].create({
                        'mo_id': production_ids[0].id,
                        'product_qty': production_ids[0].product_qty - 1
                    })
                    change_qty.with_context(skip_activity=True).change_prod_qty()

                    # production_ids[0].product_qty = production_ids[0].product_qty - 1
                else:
                    # This almost sounds like a joke but you cannot cancel a manufacturing order if workcenter e-mail is not set
                    if not self.env.user.partner_id.email:
                        self.env.user.partner_id.email = self.env.user.login
                    production_ids[0]._action_cancel()
                production_ids -= production_ids[0]
            
    def _check_scrap(self):
        print('zzz123123')
        for production_id in self:
            if production_id.to_be_scrapped:
                # This could be simplified because we already have conditional statement indicating
                # that product needs to be scrapped so conditional statements 1 and 4 will
                # always be False. I leave it for intuition behind the solution. 
                if not production_id.to_be_scrapped and not production_id.has_returned_from_repair:
                    # If product does not need scrapping and has not just returned from repair, then
                    #   1) proceed business as usual
                    return True
                elif production_id.to_be_scrapped and not production_id.has_returned_from_repair:
                    print('123123123')
                    print(production_id.location_dest_id)
                    # If product needs scrapping but has not been repaired before, then
                    #   1) Final good needs to be scrapped
                    #   2) All source (upper-level) manufacturing orders need to have their quantity to produce lowered by 1                    
                    stock_scrap = production_id.env['stock.scrap'].create({
                        'product_id': production_id.product_id.id,
                        'scrap_qty': 1, # QA checks will only be carried out on tracked-by-serial-number products so QTY will always be 1
                        'product_uom_id': production_id.product_id.uom_id.id,
                        'lot_id': production_id.lot_producing_id.id,
                        'location_id': production_id.location_dest_id.id,
                        'scrap_location_id': production_id.env['stock.location'].search([('scrap_location','=',True)],limit=1).id,
                        'origin': production_id.name,
                    })
                    stock_scrap.do_scrap()
                    production_id.discount_source_qty()
                    return True
                elif production_id.to_be_scrapped and production_id.has_returned_from_repair:
                    print('4545454545')
                    
                    # If product needs scrapping but has not been repaired before, then
                    #   1) Final good needs to be scrapped
                    #   2) All source (upper-level) manufacturing orders need to have their quantity to produce lowered by 1
                    #   3) Dummy manufacturing order should be deleted (done outside this method on return of False)
                    stock_scrap = production_id.env['stock.scrap'].create({
                        'product_id': production_id.product_id.id,
                        'scrap_qty': 1, # QA checks will only be carried out on tracked-by-serial-number products so QTY will always be 1
                        'product_uom_id': production_id.product_id.uom_id.id,
                        'lot_id': production_id.lot_producing_id.id,
                        'location_id': production_id.location_dest_id.id,
                        'scrap_location_id': production_id.env['stock.location'].search([('scrap_location','=',True)],limit=1).id,
                        'origin': production_id.name,
                    })
                    stock_scrap.do_scrap()
                    production_id.pre_repair_manufacturing_order_id.discount_source_qty()
                    return False
                elif not production_id.to_be_scrapped and production_id.has_returned_from_repair:
                    print('767676767')
                    
                    # If product does not need to be scrapped but has been repaired before, then
                    #   1) Dummy manufacturing order should be deleted (done outside this method on return of False)
                    #   2) Send product to VBZ
                    #   3) TODO: Update reserved quantities in the source production order? Although
                    #   we do action_assign on every record_production() so maybe this would be excessive
                    move = production_id.env['stock.move'].create(production_id._get_move_vals(from_prod=True, needs_repairing=False))
                    move._action_confirm()
                    move._action_assign()
                    move._action_done()
                    return False

    def _check_repairing(self):
        """
        On click of 'Repair request', we mark manufacturing order as 'needs_repairing == True, to_be_scrapped == False'.

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

        On click of 'Scrap all', we mark manufacturing order as 'needs_repairing == False, to_be_scrapped == True':
            - (1) The final good needs to be scrapped
            - (2) All source (upper-level) manufacturing orders need to have their quantity to produce lowered by 1
        
        If manufacturing order is a dummy:
            - Then the order needs to be deleted
            - We perform (2) action on original manufacturing order
        """
        for production_id in self:
            if not production_id.to_be_scrapped:
                if not production_id.needs_repairing and not production_id.has_returned_from_repair:
                    # If product does not need repairing and has not just returned from repair, then
                    #   1) proceed business as usual
                    return True
                elif production_id.needs_repairing and not production_id.has_returned_from_repair:
                    # If product needs repairing but has not been repaired before, then
                    #   1) create a repairing order
                    #   2) send it to the repairing location
                    repair_id = production_id.env['repair.order'].create(production_id._get_repair_vals())
                    move = self.env['stock.move'].create(production_id._get_move_vals(from_prod=False, needs_repairing=True))
                    move._action_confirm()
                    move._action_assign()
                    move._action_done()

                    return True
                elif production_id.needs_repairing and production_id.has_returned_from_repair:
                    # If product needs repairing but has been repaired before, then
                    #   1) create a repairing order
                    #   2) unlink manufacturing order (done outside this function on return of False)
                    #   3) send product to VBZ, then to the repairing location
                    repair_id = production_id.env['repair.order'].create(production_id._get_repair_vals())
                    move_to_vbz = production_id.env['stock.move'].create(production_id._get_move_vals(from_prod=True, needs_repairing=False))
                    move_to_repairing = production_id.env['stock.move'].create(production_id._get_move_vals(from_prod=False, needs_repairing=True))
                    for move in [move_to_vbz, move_to_repairing]:
                        move._action_confirm()
                        move._action_assign()
                        move._action_done()
                    return False
                elif not production_id.needs_repairing and production_id.has_returned_from_repair:
                    # If product does not need repairing but has been repaired before, then
                    #   1) unlink manufacturing order (done outside this function on return of False)
                    #   2) send product to VBZ
                    #   3) TODO: Update reserved quantities in the source production order? Although
                    #   we do action_assign on every record_production() so maybe this would be excessive
                    move = production_id.env['stock.move'].create(production_id._get_move_vals(from_prod=True, needs_repairing=False))
                    move._action_confirm()
                    move._action_assign()
                    move._action_done()
                    return False
            

    def _check_sn_uniqueness(self):
        """ Alert the user if the serial number as already been consumed/produced """
        if self.product_tracking == 'serial' and self.lot_producing_id:
            if self._is_finished_sn_already_produced(self.lot_producing_id):
                raise UserError(_('This serial number for product %s has already been produced', self.product_id.name))

        for move in self.move_finished_ids:
            if move.has_tracking != 'serial' or move.product_id == self.product_id:
                continue
            for move_line in move.move_line_ids:
                if self._is_finished_sn_already_produced(move_line.lot_id, excluded_sml=move_line):
                    raise UserError(_('The serial number %(number)s used for byproduct %(product_name)s has already been produced',
                                      number=move_line.lot_id.name, product_name=move_line.product_id.name))

        for move in self.move_raw_ids:
            if move.has_tracking != 'serial':
                continue
            for move_line in move.move_line_ids:
                if float_is_zero(move_line.qty_done, precision_rounding=move_line.product_uom_id.rounding):
                    continue
                message = _('The serial number %(number)s used for component %(component)s has already been consumed',
                    number=move_line.lot_id.name,
                    component=move_line.product_id.name)
                co_prod_move_lines = self.move_raw_ids.move_line_ids

                # Check presence of same sn in previous productions
                duplicates = self.env['stock.move.line'].search_count([
                    ('lot_id', '=', move_line.lot_id.id),
                    ('qty_done', '=', 1),
                    ('state', '=', 'done'),
                    ('location_dest_id.usage', '=', 'production'),
                ])
                if duplicates:
                    # Maybe some move lines have been compensated by unbuild
                    duplicates_returned = move.product_id._count_returned_sn_products(move_line.lot_id)
                    removed = self.env['stock.move.line'].search_count([
                        ('lot_id', '=', move_line.lot_id.id),
                        ('state', '=', 'done'),
                        ('location_dest_id.scrap_location', '=', True)
                    ])
                    # Either removed or unbuild
                    if not ((duplicates_returned or removed) and duplicates - duplicates_returned - removed == 0):
                        # UMINA CHANGE: this error does not make sense - if we move final product from one production location to another, then it raises error
                        # We simply turn this off in hope it doesn't cause future problems. TODO: rewrite conditional statements so this function could be used elsewhere as intended
                        # raise UserError(message)
                        pass
                # Check presence of same sn in current production
                duplicates = co_prod_move_lines.filtered(lambda ml: ml.qty_done and ml.lot_id == move_line.lot_id) - move_line
                if duplicates:
                    raise UserError(message)
