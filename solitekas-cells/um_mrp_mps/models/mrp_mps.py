# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict, namedtuple
from math import log10
from datetime import timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools.date_utils import add, subtract
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from odoo.osv.expression import OR, AND
from collections import OrderedDict

from odoo.http import request


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _make_po_get_domain(self, company_id, values, partner):
        """ Avoid to merge two RFQ for the same MPS replenish. """
        domain = super(StockRule, self)._make_po_get_domain(company_id, values, partner)
        if self.env.context.get('skip_lead_time') and values.get('date_planned') and values.get('supplier') and values.get('supplier').delay:
            #domain += (('date_planned', '=', values['date_planned']),)
            procurement_date = fields.Date.to_date(values['date_planned']) - relativedelta(
                days=int(values['supplier'].delay))
            domain += (
                ('date_order', '<=',
                 datetime.combine(procurement_date, datetime.max.time())),
                ('date_order', '>=',
                 datetime.combine(procurement_date, datetime.min.time()))
            )
        return domain


class MrpProductionSchedule(models.Model):
    _inherit = 'mrp.production.schedule'

    is_final_product = fields.Boolean("Is Final Product?")
    bom_components = fields.Integer("BoM Components")
    parent_id = fields.Many2one("mrp.production.schedule", "Parent")
    # I override product_id domain to only include produceable final product 
    # (do not confuse check-box 'is_final_product' in product.product and
    # in mrp.production.schedule, they are not related. Rename one of the checkboxes, TODO)
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True, domain="[('is_final_product','=',True)]")
    # Umina Change: we want 100million for default quantity of max to replenish
    max_to_replenish_qty = fields.Float('Maximum to Replenish', default=100000000)

    def session_store_mps_show_hide(self, action_type, is_parent=False):
        if not 'mps_row_show' in request.session:
            request.session['mps_row_show'] = {}
        else:
            if is_parent:
                if not self.id in request.session['mps_row_show']:
                    request.session['mps_row_show'][self.id] = {}

                if action_type == 'show':
                    # print('her???11')
                    request.session['mps_row_show'][self.id].update({
                        'show': True
                    })
                    request.session.modified = True
                else:
                    request.session['mps_row_show'][self.id].update({
                        'show': False
                    })
                    request.session.modified = True
        # print('here1111')
        # print(request.session)

    def hide_show_mps_row(self, action_type):
        # print('???')
        # print(productionScheduleId)
        # print(request.session)

        is_parent = True if not self.parent_id else False
        self.session_store_mps_show_hide(action_type, is_parent=is_parent)
                # child_mps = self.env['mrp.production.schedule'].search([
                #     ('parent_id', '=', self.id)
                # ])
                # print('child mps123')
                # print(child_mps)


        # if not 'mps_row_show' in request.session:
        #     request.session['mps_row_show'] = {}
        # else:
        #     request.session['mps_row_show'].update({
        #         productionScheduleId: True
        #     })

        # print('test123')
        # print(request.session['mps_row_show'])
        # print(request.session['mps_row_show'][productionScheduleId])
        return 'test1213'

    def is_mps_show(self):
        # print(request.session)
        if 'mps_row_show' in request.session:
            is_parent = True if not self.parent_id else False
            if not is_parent:
                parent_mps = self.parent_id
                # print(request.session)

                if parent_mps.id in request.session['mps_row_show'] and \
                    request.session['mps_row_show'][parent_mps.id]['show'] == True:
                    # print(request.session)
                    # print('yes there is123')
                    return True
                else:
                    return False

            else:
                print('asd123')
                print(request.session)
                print(self.id)
                if self.id in request.session['mps_row_show'] and \
                    request.session['mps_row_show'][self.id]['show'] == True:
                    # print(request.session)
                    print('yes there is123')
                    return True
                else:
                    print('no1111')
                    return False
            # if self.id in request.session['mps_row_show'] and \
            #     request.session['mps_row_show'][self.id] == True:
            #     return True
        return False


    _sql_constraints = [
        ('warehouse_product_ref_uniq', 'unique (warehouse_id, product_id, bom_id)',
         'The combination of warehouse, product and bom must be unique !'),
    ]

    def _get_indirect_demand_ratio_mps(self, indirect_demand_trees):
        """ Return {(warehouse, product): {product: ratio}} dict containing the indirect ratio
        between two products.
        """
        by_warehouse_mps = defaultdict(lambda: self.env['mrp.production.schedule'])
        for mps in self:
            by_warehouse_mps[mps.warehouse_id] |= mps

        result = defaultdict(lambda: defaultdict(float))
        for warehouse_id, other_mps in by_warehouse_mps.items():
            other_mps_product_ids = other_mps.mapped('product_id')
            subtree_visited = set()

            def _dfs_ratio_search(current_node, ratio, node_indirect=False, main_node=False):
                for child in current_node.children:
                    if child.product in other_mps_product_ids:
                        # Grover Add
                        if main_node:
                            result[(warehouse_id, main_node.product)][child.product] += ratio * child.ratio
                        # End Grover Add
                        
                        # Valentas edit: commenting out below code, because it was doubling replenish quantities for final product components
                        # result[(warehouse_id, node_indirect and node_indirect.product or current_node.product)][child.product] += ratio * child.ratio
                        
                        if child.product in subtree_visited:  # Don't visit the same subtree twice
                            continue
                        subtree_visited.add(child.product)
                        _dfs_ratio_search(child, 1.0, node_indirect=False, main_node=main_node)
                    else:  # Hidden Bom => continue DFS and set node_indirect
                        _dfs_ratio_search(child, child.ratio * ratio, node_indirect=current_node, main_node=main_node)

            for tree in indirect_demand_trees:
                _dfs_ratio_search(tree, tree.ratio, main_node=tree)

        return result

    def _get_indirect_demand_tree(self):
        """ Get the tree architecture for all the BoM and BoM line that are
        related to production schedules in self. The purpose of the tree:
        - Easier traversal than with BoM and BoM lines.
        - Allow to determine the schedules evaluation order. (compute the
        schedule without indirect demand first)
        It also made the link between schedules even if some intermediate BoM
        levels are hidden. (e.g. B1 -1-> B2 -1-> B3, schedule for B1 and B3
        are linked even if the schedule for B2 does not exist.)
        Return a list of namedtuple that represent on top the schedules without
        indirect demand and on lowest leaves the schedules that are the most
        influenced by the others.
        """
        bom_by_product = self.env['mrp.bom']._bom_find(self.product_id)

        Node = namedtuple('Node', ['product', 'ratio', 'children'])
        indirect_demand_trees = {}
        product_visited = {}

        def _get_product_tree(product, ratio):
            product_tree = product_visited.get(product)
            if product_tree:
                return Node(product_tree.product, ratio, product_tree.children)

            product_tree = Node(product, ratio, [])
            product_bom = bom_by_product[product]
            if product not in bom_by_product and not product_bom:
                product_bom = self.env['mrp.bom']._bom_find(product)[product]
            # ADD: Grover added to include boms that doesn't appear into the lines
            if not product_bom:
                product_bom = self.env['mrp.bom'].search([('product_id', '=', product.id)])
            if not product_bom:
                product_bom = self.env['mrp.bom'].search([('product_tmpl_id', '=', product.product_tmpl_id.id)])
            # END ADD: Grover added to include boms that doesn't appear into the lines
            for line in product_bom.bom_line_ids:
                line_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
                bom_qty = line.bom_id.product_uom_id._compute_quantity(line.bom_id.product_qty, line.bom_id.product_tmpl_id.uom_id)
                ratio = line_qty / bom_qty
                tree = _get_product_tree(line.product_id, ratio)
                product_tree.children.append(tree)
                if line.product_id in indirect_demand_trees:
                    del indirect_demand_trees[line.product_id]
            product_visited[product] = product_tree
            return product_tree

        for product in self.mapped('product_id'):
            if product in product_visited:
                continue
            indirect_demand_trees[product] = _get_product_tree(product, 1.0)

        return [tree for tree in indirect_demand_trees.values()]

    def _get_forecasts_state(self, production_schedule_states, date_range, procurement_date):
        """ Return the state for each forecast cells.
        - to_relaunch: A procurement has been launched for the same date range
        but a replenish modification require a new procurement.
        - to_correct: The actual replenishment is greater than planned, the MPS
        should be updated in order to match reality.
        - launched: Nothing todo. Either the cell is in the lead time range but
        the forecast match the actual replenishment. Or a foreced replenishment
        happens but the forecast and the actual demand still the same.
        - to_launch: The actual replenishment is lower than forecasted.

        It also add a tag on cell in order to:
        - to_replenish: The cell is to launch and it needs to be runned in order
        to arrive on time due to lead times.
        - forced_replenish: Cell to_launch or to_relaunch with the smallest
        period

        param production_schedule_states: schedules with a state to compute
        param date_range: list of period where a state should be computed
        param procurement_date: today + lead times for products in self
        return: the state for each time slot in date_range for each schedule in
        production_schedule_states
        rtype: dict
        """
        forecasts_state = defaultdict(list)
        for production_schedule in self:
            forecast_values = production_schedule_states[production_schedule.id]['forecast_ids']
            forced_replenish = True
            for index, (date_start, date_stop) in enumerate(date_range):
                forecast_state = {}
                forecast_value = forecast_values[index]
                existing_forecasts = production_schedule.forecast_ids.filtered(lambda p: p.date >= date_start and p.date <= date_stop)
                procurement_launched = any(existing_forecasts.mapped('procurement_launched'))

                replenish_qty = forecast_value['replenish_qty']
                incoming_qty = forecast_value['incoming_qty']
                if incoming_qty < replenish_qty and procurement_launched:
                    state = 'to_relaunch'
                elif incoming_qty > replenish_qty:
                    state = 'to_correct'
                elif incoming_qty == replenish_qty and (date_start <= procurement_date or procurement_launched):
                    state = 'launched'
                else:
                    state = 'to_launch'
                forecast_state['state'] = state

                forecast_state['forced_replenish'] = False
                forecast_state['to_replenish'] = False

                procurement_qty = replenish_qty - incoming_qty
                if forecast_state['state'] not in ('launched', 'to_correct') and procurement_qty > 0:
                    # if date_start <= procurement_date:
                    #     forecast_state['to_replenish'] = True
                    forecast_state['to_replenish'] = True # TODO: Eval this, this might cause a lot of issues, test it several before
                    if forced_replenish:
                        forecast_state['forced_replenish'] = True
                        forced_replenish = False

                forecasts_state[production_schedule.id].append(forecast_state)
        return forecasts_state

    def action_replenish(self, based_on_lead_time=False):
        filtered_schedules = self.env['mrp.production.schedule']
        for schedule in self:
            if not filtered_schedules.filtered(lambda x: x.product_id == schedule.product_id and x.warehouse_id == schedule.warehouse_id):
                filtered_schedules += schedule
        return super(MrpProductionSchedule, filtered_schedules.with_context(skip_bus=True)).action_replenish(based_on_lead_time=based_on_lead_time)

    def recalculate_components(self):
        self.ensure_one()
        bom = self.bom_id
        components_list = set()
        components_vals = []

        dummy, components = bom.explode(self.product_id, 1)
        current_component_products = [x.product_id.id for x in self.env['mrp.production.schedule'].search([('parent_id', '=', self.id)])]
        for component in components:
            components_list.add((component[0].product_id.id, self.warehouse_id.id, self.company_id.id, self.id))
            if component[0].product_id.id in current_component_products:
                current_component_products.remove(component[0].product_id.id)

        #Remove the missing ones
        self.env['mrp.production.schedule'].search([('parent_id', '=', self.id), ('product_id', 'in', current_component_products)]).unlink()

        for component in components_list:
            if self.env['mrp.production.schedule'].search_count([
                ('product_id', '=', component[0]),
                ('warehouse_id', '=', component[1]),
                ('company_id', '=', component[2]),
                ('parent_id', '=', self.id),
            ]):
                continue
            components_vals.append({
                'product_id': component[0],
                'warehouse_id': component[1],
                'company_id': component[2],
                'parent_id': component[3],
            })
        if components_vals:
            self.env['mrp.production.schedule'].create(components_vals)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """ If the BoM is pass at the creation, create MPS for its components """
        mps = super(models.Model, self).create(vals_list)
        components_list = set()
        components_vals = []
        for record in mps:
            bom = record.bom_id
            if not bom:
                continue
            record.is_final_product = True
            dummy, components = bom.explode(record.product_id, 1)

            child_bom_ids = []

            for component in components:
                # If this has child don't add components
                if component[0].child_bom_id:
                    child_bom_ids.append((component[0].child_bom_id, component[0].product_id))
                else:
                    components_list.add((component[0].product_id.id, record.warehouse_id.id, record.company_id.id, record.id))

            while child_bom_ids:
                dummy_child, components_child = child_bom_ids[0][0].explode(child_bom_ids[0][1], 1)
                child_bom_ids.remove(child_bom_ids[0])

                for component_child in components_child:
                    if component_child[0].child_bom_id:
                        child_bom_ids.append((component_child[0].child_bom_id, component_child[0].product_id))
                    else:
                        components_list.add((component_child[0].product_id.id, record.warehouse_id.id, record.company_id.id, record.id))


        for component in components_list:
            # if self.env['mrp.production.schedule'].search_count([
            #     ('product_id', '=', component[0]),
            #     ('warehouse_id', '=', component[1]),
            #     ('company_id', '=', component[2]),
            # ]):
            #     continue
            components_vals.append({
                'product_id': component[0],
                'warehouse_id': component[1],
                'company_id': component[2],
                'parent_id': component[3],
            })
        if components_vals:
            self.env['mrp.production.schedule'].create(components_vals)
        return mps

    def write(self, vals):
        res = super(MrpProductionSchedule, self).write(vals)
        if 'max_to_replenish_qty' in vals or 'min_to_replenish_qty' in vals:
            for schedule in self:
                scheduled_ids = self.search([('product_id', '=', schedule.product_id.id), ('warehouse_id', '=', schedule.warehouse_id.id), ('company_id', '=', schedule.company_id.id), ('id', '!=', schedule.id)])
                if scheduled_ids:
                    super(MrpProductionSchedule, scheduled_ids).write({'min_to_replenish_qty': schedule.min_to_replenish_qty, 'max_to_replenish_qty': schedule.max_to_replenish_qty})
                    self.env['bus.bus']._sendone('mrp_mps_channel', 'refresh_mps', {'product_ids': [s.product_id.id for s in scheduled_ids]})
        return res


    def unlink(self):
        for schedule in self:
            self.search([('parent_id', '=', schedule.id)]).unlink()
        return super(MrpProductionSchedule, self).unlink()
    
    def _get_rfq_confirmed_domain(self, date_start, date_stop):
        """ Return a domain used to compute the incoming quantity for a given
        product/warehouse/company.

        :param date_start: start date of the forecast domain
        :param date_stop: end date of the forecast domain
        """
        return [
            # ('order_id.picking_type_id.default_location_dest_id', 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('order_id.date_planned_mps', '!=', False),
            ('product_id', 'in', self.mapped('product_id').ids),
            ('state', 'in', ('purchase', 'done')),
            ('date_planned', '>=', date_start),
            ('date_planned', '<=', date_stop)
        ]

    def _get_confirmed_incoming_qty(self, date_range):
        """ Get the incoming quantity from RFQ and existing moves.

        param: list of time slots used in order to group incoming quantity.
        return: a dict with as key a production schedule and as values a list
        of incoming quantity for each date range.
        """
        incoming_qty = defaultdict(float)
        incoming_qty_done = defaultdict(float)
        after_date = date_range[0][0]
        before_date = date_range[-1][1]
        # Get quantity in RFQ
        rfq_domain = self._get_rfq_confirmed_domain(after_date, before_date)
        rfq_lines = self.env['purchase.order.line'].search(rfq_domain, order='date_planned')
        index = 0
        for line in rfq_lines:
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= line.date_planned.date() and
                       date_range[index][1] >= line.date_planned.date()):
                index += 1
            quantity = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            incoming_qty[date_range[index], line.product_id, line.order_id.picking_type_id.warehouse_id] += quantity

        # Get quantity on incoming moves
        # TODO: issue since it will use one search by move. Should use a
        # read_group with a group by location.
        domain_moves = self._get_moves_domain(after_date, before_date, 'incoming')
        stock_moves = self.env['stock.move'].search(domain_moves, order='date')
        index = 0
        for move in stock_moves:
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= move.date.date() and date_range[index][1] >= move.date.date()):
                index += 1
            key = (date_range[index], move.product_id, move.location_dest_id.warehouse_id)
            if move.state == 'done':
                incoming_qty_done[key] += move.product_qty
            # else:
            #     incoming_qty[key] += move.product_qty # Disabling due we are not going to compute double RFQ and picking

        return incoming_qty, incoming_qty_done

    def _get_rfq_draft_domain(self, date_start, date_stop):
        """ Return a domain used to compute the incoming quantity for a given
        product/warehouse/company.

        :param date_start: start date of the forecast domain
        :param date_stop: end date of the forecast domain
        """
        return [
            ('order_id.picking_type_id.default_location_dest_id', 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('product_id', 'in', self.mapped('product_id').ids),
            ('state', '=', 'draft'),
            ('date_planned', '>=', date_start),
            ('date_planned', '<=', date_stop)
        ]

    def _get_incoming_delayed_errors(self, date_range):
        """ Get if between purchase order lines there are lines that are not possible to arrive on time
        """
        delayed_errors = defaultdict(float)
        after_date = date_range[0][0]
        before_date = date_range[-1][1]
        # Get quantity in RFQ
        rfq_domain = self._get_rfq_draft_domain(after_date, before_date)
        rfq_lines = self.env['purchase.order.line'].search(rfq_domain, order='date_planned')

        index = 0
        for line in rfq_lines:
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= line.date_planned.date() and
                       date_range[index][1] >= line.date_planned.date()):
                index += 1
            if line.order_id.date_order < fields.Datetime.now() and line.order_id.state == 'draft':
                delayed_errors[date_range[index], line.product_id, line.order_id.picking_type_id.warehouse_id] = 'Order %s might arrive late' % line.order_id.name

        return delayed_errors

    def _get_moves_domain(self, date_start, date_stop, type):
        """ Return domain for incoming or outgoing moves """
        if not self:
            return [('id', '=', False)]
        location = type == 'incoming' and 'location_dest_id' or 'location_id'
        location_dest = type == 'incoming' and 'location_id' or 'location_dest_id'
        domain = []

        common_domain = [
            ('state', 'not in', ['cancel', 'draft']),
            (location + '.usage', '!=', 'inventory'),
            '|',
                (location_dest + '.usage', 'not in', ('internal', 'inventory')),
                '&',
                (location_dest + '.usage', 'in', ('internal',)),
                '!',
                    (location_dest, 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('is_inventory', '=', False),
            ('date', '<=', date_stop),
        ]
        
        # if type == 'outgoing':
        #     common_domain += [(location_dest, 'child_of', self.env.ref('um_mrp_data.stock_production').id)]

        groupby_delay = defaultdict(list)
        for schedule in self:
            rules = schedule.product_id._get_rules_from_location(schedule.warehouse_id.lot_stock_id)
            delay, dummy = rules.filtered(lambda r: r.action not in ['buy', 'manufacture'])._get_lead_days(schedule.product_id)
            groupby_delay[delay].append((schedule.product_id, schedule.warehouse_id))
        for delay in groupby_delay:
            products, warehouses = zip(*groupby_delay[delay])
            warehouses = self.env['stock.warehouse'].concat(*warehouses)
            products = self.env['product.product'].concat(*products)

            specific_domain = [
                (location, 'child_of', warehouses.mapped('view_location_id').ids),
                ('product_id', 'in', products.ids),
                ('date', '>=', date_start - relativedelta(days=delay)),
            ]
            domain = OR([domain, AND([common_domain, specific_domain])])
        return domain

    def _get_moves_and_date(self, moves_domain, order=False):
        moves = self.env['stock.move'].search(moves_domain, order=order)
        res_moves = []
        for move in moves:

            # if move.id == 17939:
            #     print('test123')
            #     print('test123')
            
            if not move.move_dest_ids:
                res_moves.append((move, fields.Date.to_date(move.date)))
                continue
            elif move.move_dest_ids:
                delay = max(move.move_dest_ids.mapped(lambda m: self._get_dest_moves_delay(m)))
                date = fields.Date.to_date(move.date) + relativedelta(days=delay)
                res_moves.append((move, date))
        return res_moves

    def _get_outgoing_qty(self, date_range, move_type=False):
        """ Get the outgoing quantity from existing moves.
        return a dict with as key a production schedule and as values a list
        of outgoing quantity for each date range.
        """
        outgoing_qty = defaultdict(float)
        outgoing_qty_done = defaultdict(float)
        after_date = date_range[0][0]
        before_date = date_range[-1][1]
        # Get quantity on incoming moves

        domain_moves = self._get_moves_domain(after_date, before_date, 'outgoing')
        if move_type != 'with_manufacturing':
            domain_moves = AND([domain_moves, [('raw_material_production_id', '=', False)]])
            
        domain_moves = AND([domain_moves, [('state', '=', 'done')]])

        stock_moves_by_date = self._get_moves_and_date(domain_moves)
        stock_moves_by_date = sorted(stock_moves_by_date, key=lambda m: m[1])
        index = 0

        # # print(stock_moves_by_date)
        # # print(date_range)
        # # print(len(stock_moves_by_date))
        # print('this123bbbzzz')
        # print(stock_moves_by_date)
        # test = [i for i in stock_moves_by_date if i[0].id == 17939]
        # if test:
        #     print('here111')
        #     print(domain_moves)
        #     print(after_date)
        #     print(before_date)
        #     print(test)

        
        # if after_date == datetime(2022, 10, 3).date() and \
        #     before_date == datetime(2022, 12, 25).date():
        #     print('zzzzzaaa')
        #     print(domain_moves)
        #     print(after_date)
        #     print(before_date)
        #     # print(type)
        #     # print(domain_moves)
        #     print(stock_moves_by_date)

        for (move, date) in stock_moves_by_date:

            # There are cases when we want to consider moves where their (scheduled) date occurs before the after_date
            # if lead times make their stock delivery at a relevant time. Therefore we need to ignore the lines that have
            # date + lead time < after_date
            if date < after_date:
                continue
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= date and date_range[index][1] >= date):
                index += 1
            key = (date_range[index], move.product_id, move.location_id.warehouse_id)

            # if move.product_id.id == 2079:
            #     print('this123bbb')
                # print(type)
                # print(domain_moves)
                # print(stock_moves_by_date)

            #umina edit: added or move.location_dest_id.location_id.usage == 'production'
            #Because the number calculated was wrong with current custom odoo configuration made for solitekas cells.
            # ADD: Rule added:
            if move.location_dest_id.usage == 'customer' or move.location_dest_id.location_id.usage == 'production' or (move.picking_id and move.picking_id.picking_type_id and move.picking_id.picking_type_id.code == 'outgoing'):
            # End rule added
                if move.state == 'done':
                    outgoing_qty_done[key] += move.product_uom_qty
                else:
                    outgoing_qty[key] += move.product_uom_qty
                    
        return outgoing_qty, outgoing_qty_done


    def _get_outgoing_qty_actual_demand(self, date_range, move_type=False):
        outgoing_qty = defaultdict(float)
        outgoing_qty_done = defaultdict(float)
        after_date = date_range[0][0]
        before_date = date_range[-1][1]
        # Get quantity on incoming moves

        domain_moves = self._get_moves_domain(after_date, before_date, 'outgoing')
        domain_moves = AND([domain_moves, [('raw_material_production_id', '=', False)]])
        stock_moves_by_date = self._get_moves_and_date(domain_moves)
        stock_moves_by_date = sorted(stock_moves_by_date, key=lambda m: m[1])
        index = 0
        for (move, date) in stock_moves_by_date:
            # There are cases when we want to consider moves where their (scheduled) date occurs before the after_date
            # if lead times make their stock delivery at a relevant time. Therefore we need to ignore the lines that have
            # date + lead time < after_date
            if date < after_date:
                continue
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= date and date_range[index][1] >= date):
                index += 1
            key = (date_range[index], move.product_id, move.location_id.warehouse_id)
            if move.state == 'done':
                outgoing_qty_done[key] += move.product_uom_qty
            else:
                outgoing_qty[key] += move.product_uom_qty

        return outgoing_qty, outgoing_qty_done

    def get_production_schedule_view_state(self):
        """ Prepare and returns the fields used by the MPS client action.
        For each schedule returns the fields on the model. And prepare the cells
        for each period depending the manufacturing period set on the company.
        The forecast cells contains the following information:
        - forecast_qty: Demand forecast set by the user
        - date_start: First day of the current period
        - date_stop: Last day of the current period
        - replenish_qty: The quantity to replenish for the current period. It
        could be computed or set by the user.
        - replenish_qty_updated: The quantity to replenish has been set manually
        by the user.
        - starting_inventory_qty: During the first period, the quantity
        available. After, the safety stock from previous period.
        - incoming_qty: The incoming moves and RFQ for the specified product and
        warehouse during the current period.
        - outgoing_qty: The outgoing moves quantity.
        - indirect_demand_qty: On manufacturing a quantity to replenish could
        require a need for a component in another schedule. e.g. 2 product A in
        order to create 1 product B. If the replenish quantity for product B is
        10, it will need 20 product A.
        - safety_stock_qty:
        starting_inventory_qty - forecast_qty - indirect_demand_qty + replenish_qty
        """
        company_id = self.env.company
        date_range = company_id._get_date_range()
        date_range_year_minus_1 = company_id._get_date_range(years=1)
        date_range_year_minus_2 = company_id._get_date_range(years=2)

        # We need to get the schedule that impact the schedules in self. Since
        # the state is not saved, it needs to recompute the quantity to
        # replenish of finished products. It will modify the indirect
        # demand and replenish_qty of schedules in self.
        schedules_to_compute = self.env['mrp.production.schedule'].browse(self.get_impacted_schedule()) | self

        # Dependencies between schedules
        indirect_demand_trees = schedules_to_compute._get_indirect_demand_tree()

        indirect_ratio_mps = schedules_to_compute._get_indirect_demand_ratio_mps(indirect_demand_trees)

        # Get the schedules that do not depends from other in first position in
        # order to compute the schedule state only once.
        indirect_demand_order = schedules_to_compute._get_indirect_demand_order(indirect_demand_trees)
        indirect_demand_qty = defaultdict(float)
        quantity_component = defaultdict(float)
        replenishment_component = defaultdict(float)
        # Added by Umina
        max_replenishment_component = defaultdict(float)
        # End
        incoming_qty, incoming_qty_done = self._get_incoming_qty(date_range)
        incoming_confirmed_qty, incoming_confirmed_qty_done = self._get_confirmed_incoming_qty(date_range)
        delayed_errors = self._get_incoming_delayed_errors(date_range)
        outgoing_qty, outgoing_qty_done = self._get_outgoing_qty(date_range, 'with_manufacturing')
        outgoing_qty_without_mo, outgoing_qty_done_without_mo = self._get_outgoing_qty(date_range)
        
        outgoing_qty_actual_demand, outgoing_qty_done_actual_demand = self._get_outgoing_qty_actual_demand(date_range)

        dummy, outgoing_qty_year_minus_1 = self._get_outgoing_qty(date_range_year_minus_1)
        dummy, outgoing_qty_year_minus_2 = self._get_outgoing_qty(date_range_year_minus_2)
        read_fields = [
            'forecast_target_qty',
            'min_to_replenish_qty',
            'max_to_replenish_qty',
            'product_id',
            'parent_id',
        ]
        if self.env.user.has_group('stock.group_stock_multi_warehouses'):
            read_fields.append('warehouse_id')
        if self.env.user.has_group('uom.group_uom'):
            read_fields.append('product_uom_id')
        production_schedule_states = schedules_to_compute.read(read_fields)
        production_schedule_states_by_id = {mps['id']: mps for mps in production_schedule_states}
        for production_schedule in indirect_demand_order:
            product_variations = production_schedule.product_id.product_tmpl_id.product_variant_ids
            # Bypass if the schedule is only used in order to compute indirect
            # demand.
            rounding = production_schedule.product_id.uom_id.rounding
            lead_time = production_schedule._get_lead_times()
            production_schedule_state = production_schedule_states_by_id[production_schedule['id']]
            if production_schedule in self:
                procurement_date = add(fields.Date.today(), days=lead_time)
                precision_digits = max(0, int(-(log10(production_schedule.product_uom_id.rounding))))
                production_schedule_state['precision_digits'] = production_schedule.parent_id and precision_digits or 0 # Added by request
                production_schedule_state['forecast_ids'] = []

            # starting_inventory_qty = production_schedule.product_id.with_context(
            #     warehouse=production_schedule.warehouse_id.id).qty_available

            starting_inventory_qty = production_schedule.product_id.with_context(
                warehouse=production_schedule.warehouse_id.id).qty_available

            if production_schedule.product_id.is_final_product:
                #Umina edit: If product is final product, get also the product variants and its qties because
                #of customly made functioanlity for solitekas cells where they produce product variations on manufacturing.
                starting_inventory_qty = sum(product_variations.mapped(
                    lambda x: x.with_context(
                        warehouse=production_schedule.warehouse_id.id).qty_available
                ))

            if len(date_range):
                for prd_vartiation in product_variations:
                    starting_inventory_qty -= incoming_qty_done.get(
                        (date_range[0], prd_vartiation, production_schedule.warehouse_id), 0.0)
                    starting_inventory_qty += outgoing_qty_done.get(
                        (date_range[0], prd_vartiation, production_schedule.warehouse_id), 0.0)
                
                # starting_inventory_qty -= incoming_qty_done.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                # starting_inventory_qty += outgoing_qty_done.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)

                # if production_schedule.product_id.id == 2079 and starting_inventory_qty < 0:
                #     print('here123')
                #     print(date_range[0])
                #     print(outgoing_qty_done.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0))
                #     print(incoming_qty_done.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0))

                # starting_inventory_qty_without_mo -= incoming_qty_done.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                # starting_inventory_qty_without_mo += outgoing_qty_without_mo.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)

                # starting_inventory_qty += 10
                # if production_schedule.product_id.id == 2075:
                # if production_schedule.product_id.id == 2079:
                #     print('here123')
                #     print(production_schedule.product_id)
                #     print(incoming_qty_done.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0))
                #     print(outgoing_qty_done.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0))

            if production_schedule.id == 759:
                print('here123test123')
                print(production_schedule.is_mps_show())
            production_schedule_state['mps_row_show'] = production_schedule.is_mps_show()


            if production_schedule.product_id.product_tmpl_id.bom_count > 0:
                production_schedule_state['is_final_product'] = True
                production_schedule_state['bom_components'] = len(
                    production_schedule.product_id.product_tmpl_id.bom_ids[0].bom_line_ids)
            else:
                production_schedule_state['is_final_product'] = False
                production_schedule_state['bom_components'] = 0

            for index, (date_start, date_stop) in enumerate(date_range):
                forecast_values = {}
                key = ((date_start, date_stop), production_schedule.product_id, production_schedule.warehouse_id)
                key_y_1 = (date_range_year_minus_1[index], *key[1:])
                key_y_2 = (date_range_year_minus_2[index], *key[1:])
                existing_forecasts = production_schedule.forecast_ids.filtered(
                    lambda p: p.date >= date_start and p.date <= date_stop)

                if production_schedule in self:
                    forecast_values['date_start'] = date_start
                    forecast_values['date_stop'] = date_stop

                    
                    forecast_values['incoming_qty'] = float_round(incoming_qty.get(key, 0.0) + incoming_qty_done.get(key, 0.0), precision_rounding=rounding)
                
                    # if production_schedule.product_id.id == 2105:
                    #     print('ttt123123')
                    #     print(incoming_confirmed_qty)
                        # print(float_round(incoming_confirmed_qty.get(key, 0.0), precision_rounding=rounding))
                    
                    # ADDED: Added to get also the incoming qty confirmed
                    forecast_values['incoming_qty_confirmed'] = float_round(incoming_confirmed_qty.get(key, 0.0), precision_rounding=rounding)
                    # End Add

                    # if production_schedule.product_id.id == 2759:
                    #     print('test123123')
                    #     print(outgoing_qty_without_mo.get(key, 0.0))
                    #     print(outgoing_qty_done_without_mo.get(key, 0.0))

                    forecast_values['outgoing_qty'] = float_round(outgoing_qty_without_mo.get(key, 0.0) + outgoing_qty_done_without_mo.get(key, 0.0), precision_rounding=rounding)
                    # forecast_values['outgoing_qty'] = float_round(outgoing_qty_without_mo.get(key, 0.0) + outgoing_qty_done_without_mo.get(key, 0.0), precision_rounding=rounding)
                    
                    forecast_values['outgoing_qty_actual_demand'] = float_round(outgoing_qty_actual_demand.get(key, 0.0) + outgoing_qty_done_actual_demand.get(key, 0.0), precision_rounding=rounding)

                    forecast_values['outgoing_qty_year_minus_1'] = float_round(outgoing_qty_year_minus_1.get(key_y_1, 0.0), precision_rounding=rounding)
                    forecast_values['outgoing_qty_year_minus_2'] = float_round(outgoing_qty_year_minus_2.get(key_y_2, 0.0), precision_rounding=rounding)
                    forecast_values['components_not_available_message'] = delayed_errors.get(key)
                    if delayed_errors.get(key):
                        forecast_values['components_not_available'] = True

                forecast_values['indirect_demand_qty'] = float_round(indirect_demand_qty.get(key, 0.0), precision_rounding=rounding)
                
                # if production_schedule.product_id.id == 2079 :
                # # if production_schedule.product_id.id == 2079 and starting_inventory_qty < 0:
                #     # print('difference1233')
                #     # print(starting_inventory_qty)

                #     # outgoing_qty, outgoing_qty_done = self._get_outgoing_qty(date_range, 'with_manufacturing')
                #     # outgoing_qty_without_mo, outgoing_qty_done_without_mo = self._get_outgoing_qty(date_range)

                #     test1 = outgoing_qty_done.get(
                #         (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                #     test2 = incoming_qty_done.get(
                #         (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                    # print(test1)
                    # print(test2)

                    # test3 = outgoing_qty.get(
                    #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                    # test4 = outgoing_qty_done_without_mo.get(
                    #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                    

                    # forecast_values['indirect_demand_qty'] = float_round(indirect_demand_qty.get(key, 0.0) - difference, precision_rounding=rounding)

                replenish_qty_updated = False
                # Added: min_qty
                min_qty = 0.0
                # End Add
                if existing_forecasts:
                    # ADDED: Added conditions to avoid less num than actual demand
                    replenish_qty = float_round(sum(existing_forecasts.mapped('forecast_qty')), precision_rounding=rounding)
                    if 'outgoing_qty' in forecast_values and forecast_values['outgoing_qty'] > float_round(sum(existing_forecasts.mapped('forecast_qty')), precision_rounding=rounding):
                        existing_forecasts[0].forecast_qty = existing_forecasts[0].forecast_qty + (forecast_values['outgoing_qty'] - replenish_qty)
                    # End Add
                    forecast_values['forecast_qty'] = float_round(sum(existing_forecasts.mapped('forecast_qty')), precision_rounding=rounding)
                    forecast_values['replenish_qty'] = float_round(sum(existing_forecasts.mapped('replenish_qty')), precision_rounding=rounding)

                    # ADDED
                    # If there is already a forecast and that forecast has a higher value than the planned one we will
                    # set the value as the incoming qty. Only on load we will set that value.
                    if 'on_get_mps_view_state' in self.env.context and 'incoming_qty' in forecast_values and forecast_values['incoming_qty'] != 0.0 and forecast_values['incoming_qty'] < forecast_values['replenish_qty']:
                        forecast_values['replenish_qty'] = forecast_values['incoming_qty']
                        # If the length of the existing forecasts is only 1 (it should be all the time)
                        # we will update, since it's stored on db, and the upper trick will only display
                        # the value, but we need to store it on db
                        if len(existing_forecasts) == 1:
                            existing_forecasts.replenish_qty = forecast_values['incoming_qty']
                    # END ADDED

                    # Check if the to replenish quantity has been manually set or
                    # if it needs to be computed.
                    replenish_qty_updated = any(existing_forecasts.mapped('replenish_qty_updated'))
                    forecast_values['replenish_qty_updated'] = replenish_qty_updated

                    # ADDED: The quantity needs to be at least the minimum
                    min_qty = existing_forecasts.production_schedule_id.min_to_replenish_qty
                    if forecast_values['replenish_qty'] < existing_forecasts.production_schedule_id.min_to_replenish_qty:
                        forecast_values['replenish_qty'] = existing_forecasts.production_schedule_id.min_to_replenish_qty
                        forecast_values['replenish_qty_updated'] = True
                    # End Add
                else:
                    # ADDED: . REPLACES: forecast_values['forecast_qty'] = 0.0
                    if 'outgoing_qty' in forecast_values and forecast_values['outgoing_qty']:
                        forecast_values['forecast_qty'] = forecast_values['outgoing_qty']
                    else:
                        forecast_values['forecast_qty'] = 0.0
                    # FINAL ADDED

                if not replenish_qty_updated:
                    replenish_qty = production_schedule._get_replenish_qty(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'])
                    # ADDED: We test here if the record is higher than 0. Replaces: forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                    # if replenish_qty and existing_forecasts and existing_forecasts.replenish_qty > 0:
                    #     forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                    # else:
                    #     forecast_values['replenish_qty'] = float_round(0.0, precision_rounding=rounding)
                    if min_qty > replenish_qty:
                        replenish_qty = min_qty
                    # if replenish_qty and forecast_values['indirect_demand_qty'] >= starting_inventory_qty:  #Client said they're not sure if they want '>=' or '>'
                    #     forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                    if replenish_qty and forecast_values['indirect_demand_qty'] > starting_inventory_qty:
                        forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                    else:
                        forecast_values['replenish_qty'] = float_round(0.0, precision_rounding=rounding)
                    forecast_values['replenish_qty_updated'] = False
                    # End Add

                # if not replenish_qty_updated:
                #     replenish_qty = production_schedule._get_replenish_qty(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'])
                #     forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                #     forecast_values['replenish_qty_updated'] = False
                    
                #     # # ADDED: We test here if the record is higher than 0. Replaces: forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                #     # # if replenish_qty and existing_forecasts and existing_forecasts.replenish_qty > 0:
                #     # #     forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                #     # # else:
                #     # #     forecast_values['replenish_qty'] = float_round(0.0, precision_rounding=rounding)
                #     # if min_qty > replenish_qty:
                #     #     replenish_qty = min_qty
                #     # # if replenish_qty and forecast_values['indirect_demand_qty'] >= starting_inventory_qty:  #Client said they're not sure if they want '>=' or '>'
                #     # #     forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                #     # if replenish_qty and forecast_values['indirect_demand_qty'] >= starting_inventory_qty:  # Added by Grover: Even if client is not sure, >= is applied to this case, but > doesn't work
                #     #     forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                #     # else:
                #     #     forecast_values['replenish_qty'] = float_round(0.0, precision_rounding=rounding)
                #     # forecast_values['replenish_qty_updated'] = False
                #     # # End Add

                # outgoing_qty, outgoing_qty_done = self._get_outgoing_qty(date_range)
                # outgoing_qty_with_mo_int = outgoing_qty_with_mo.get(
                #     (date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)

                # add_outoing_qty = 0
                # print('???')
                # print(outgoing_qty_with_mo_int)
                # if outgoing_qty_with_mo_int > 0:
                #     add_outoing_qty = outgoing_qty_with_mo_int - outgoing_qty

                forecast_values['starting_inventory_qty'] = float_round(starting_inventory_qty, precision_rounding=rounding) 
                # if production_schedule.product_id.id == 2079 and starting_inventory_qty < 0:
                #     print('therezzz')
                #     print(starting_inventory_qty)
                    

                # forecast_values['safety_stock_qty'] = float_round(starting_inventory_qty_without_mo  - forecast_values['indirect_demand_qty'] + forecast_values['replenish_qty'], precision_rounding=rounding)
                forecast_values['safety_stock_qty'] = float_round(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'] + forecast_values['replenish_qty'] - forecast_values['outgoing_qty_actual_demand'], precision_rounding=rounding)
                

                # How much can we build with starting inventory
                for (product, ratio) in indirect_ratio_mps[
                    (production_schedule.warehouse_id, production_schedule.product_id)].items():
                    quantity_component[(production_schedule.product_id, product, date_start, date_stop, ratio)] = 0.0
                    replenishment_component[
                        (production_schedule.product_id, product, date_start, date_stop, ratio)] = 0.0
                    # Added by Umina
                    max_replenishment_component[(production_schedule.product_id, product, date_start, date_stop, ratio)] = 0.0
                    # End

                # How much the products have on inventory
                for (pp, pc, ds1, ds2, ratio) in quantity_component:
                    if ds1 == date_start and ds2 == date_stop and pc == production_schedule.product_id:
                        quantity_component[(pp, pc, ds1, ds2, ratio)] += starting_inventory_qty / ratio
                        replenishment_component[(pp, pc, ds1, ds2, ratio)] += forecast_values['replenish_qty'] / ratio
                        # Added by Umina
                        max_replenishment_component[(pp, pc, ds1, ds2, ratio)] = production_schedule.max_to_replenish_qty / ratio
                        # End

                if production_schedule in self:
                    production_schedule_state['forecast_ids'].append(forecast_values)
                starting_inventory_qty = forecast_values['safety_stock_qty']
                if not forecast_values['replenish_qty']:
                    continue
                # Set the indirect demand qty for children schedules.
                for (product, ratio) in indirect_ratio_mps[
                    (production_schedule.warehouse_id, production_schedule.product_id)].items():
                    related_date = max(subtract(date_start, days=lead_time), fields.Date.today())
                    index = next(i for i, (dstart, dstop) in enumerate(date_range) if
                                 related_date <= dstart or (related_date >= dstart and related_date <= dstop))
                    related_key = (date_range[index], product, production_schedule.warehouse_id)
                    indirect_demand_qty[related_key] += ratio * forecast_values['replenish_qty']

            if production_schedule in self:
                # The state is computed after all because it needs the final
                # quantity to replenish.
                forecasts_state = production_schedule._get_forecasts_state(production_schedule_states_by_id, date_range,
                                                                           procurement_date)
                forecasts_state = forecasts_state[production_schedule.id]
                for index, forecast_state in enumerate(forecasts_state):
                    production_schedule_state['forecast_ids'][index].update(forecast_state)

                # The purpose is to hide indirect demand row if the schedule do not
                # depends from another.
                has_indirect_demand = any(
                    forecast['indirect_demand_qty'] != 0 for forecast in production_schedule_state['forecast_ids'])
                production_schedule_state['has_indirect_demand'] = has_indirect_demand

        error_weeks = []
        for pss in production_schedule_states:
            for fcs in pss.get('forecast_ids', []):
                if fcs.get('components_not_available'):
                    error_weeks.append((fcs['date_start'], fcs['date_stop']))

        for pss in production_schedule_states:
            i = 0
            for fcs in pss.get('forecast_ids', []):
                i += 1
                component_availability = 0.0
                component_replenishment = 0.0
                for (pp, pc, ds1, ds2, ratio), qc in quantity_component.items():
                    if pp.id == pss['product_id'][0] and fcs['date_start'] == ds1 and fcs['date_stop'] == ds2:
                        if component_availability and qc < component_availability:
                            component_availability = qc
                        elif not component_availability:
                            component_availability = qc

                        rc = replenishment_component[(pp, pc, ds1, ds2, ratio)]
                        mrc = max_replenishment_component[(pp, pc, ds1, ds2, ratio)]  # This was Added MRC to get maximum
                        if component_replenishment and mrc < component_replenishment:
                            component_replenishment = mrc
                        elif not component_replenishment:
                            component_replenishment = mrc
                fcs['component_availability'] = component_availability
                fcs['component_replenishment'] = component_replenishment
                if (fcs['date_start'], fcs['date_stop']) in error_weeks and (fcs['components_not_available_message'] or pss['is_final_product']):
                    fcs['state'] = 'to_correct'

                context = dict(self.env.context)
                if not context.get('parent_function', False):
                    if fcs['incoming_qty'] and fcs['incoming_qty'] > fcs['replenish_qty']:
                        self.browse(pss['id']).set_replenish_qty(i - 1, fcs['incoming_qty'])
                        return self.with_context(parent_function=True).get_production_schedule_view_state()
                
                    # if pss['is_final_product'] and fcs['replenish_qty'] > component_availability:
                    #     self.browse(pss['id']).set_replenish_qty(i - 1, component_availability)
                    #     return self.with_context(parent_function=True).get_production_schedule_view_state()

        return [p for p in production_schedule_states if p['id'] in self.ids]
    

    @api.model
    def get_mps_view_state(self, domain=False):
        res = super(MrpProductionSchedule, self.with_context(on_get_mps_view_state=True)).get_mps_view_state(domain=domain)
        res['production_schedule_ids'] = sorted(res['production_schedule_ids'], key=lambda d: d['id'])
        return res

    def remove_replenish_orders(self, date_index):
        """ Remove the quantity to replenish on the forecast cell.

        param date_index: index of the period used to find start and stop date
        where the manual replenish quantity should be remove.
        """
        date_start, date_stop = self.env.user.company_id._get_date_range()[date_index]
        self = self.search([])
        domain_moves = self._get_moves_domain(date_start, date_stop, 'incoming')
        moves_by_date = self._get_moves_and_date(domain_moves)
        move_ids = self._filter_moves(moves_by_date, date_start, date_stop)

        manufacturing_orders = move_ids.filtered(lambda x: x.production_id).mapped('production_id')

        #Cancel MO's only if they didint started yet.
        mo_started = any(x in ('progress', 'to_close', 'done') for x in manufacturing_orders.mapped('child_production_ids.state'))
        if not mo_started:
            manufacturing_orders.action_cancel()

            rfq_domain = self._get_rfq_domain(date_start, date_stop)
            purchase_order_by_date = self._get_rfq_and_planned_date(rfq_domain, date_start, date_stop)
            purchase_order_line_ids = self._filter_rfq(purchase_order_by_date, date_start, date_stop)

            purchase_orders = purchase_order_line_ids.mapped('order_id')
            purchase_orders.button_cancel()
            return True
        return False

class MrpProductForecast(models.Model):
    _inherit = 'mrp.product.forecast'

    component_availability = fields.Float("Component Availability")
    component_replenishment = fields.Float("Component Replenishment")
    components_not_available = fields.Boolean("Components not Available")


class MrpMpsForecastDetails(models.TransientModel):
    _inherit = "mrp.mps.forecast.details"

    def action_open_rfq_details(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': self.env.context.get('action_name'),
            'domain': [('id', 'in', self.purchase_order_line_ids.mapped('order_id').ids)],
            'context': {'no_breadcrumbs': True},
        }

    def action_open_mo_details(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': self.env.context.get('action_name'),
            'domain': [('id', 'in', self.move_ids.mapped('production_id').ids)],
            'context': {'no_breadcrumbs': True},
        }

    def action_open_incoming_moves_details(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': self.env.context.get('action_name'),
            'domain': [('id', 'in', self.move_ids.mapped('picking_id').ids)],
            'context': {'no_breadcrumbs': True},
        }