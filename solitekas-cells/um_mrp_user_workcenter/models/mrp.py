
import logging
import math
import re
from odoo import models, fields, _, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SIZE_BACK_ORDER_NUMERING = 3


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Hack for _should_bypass_reservation on split
    def _should_bypass_reservation(self, forced_location=False):
        if not self:  # When doing _split_productions move_id is cleared
            return True
        res = super(StockMove, self)._should_bypass_reservation(
            forced_location=forced_location)
        return bool(res and not self.production_id)

class StockProductionLotUmina(models.Model):
    _inherit= 'stock.production.lot'

    stc_vbz_qty = fields.Float('VBZ Quantity', compute='_get_stc_vbz_qty', store=False)

    def _get_stc_vbz_qty(self):
        for lot in self:
            available_lot_ids = lot.env['stock.quant'].search([('lot_id','=',lot.id),('quantity','>',0),('product_id', '=', lot.product_id.id),('location_id.is_stc_vbz','=',True)])
            lot.stc_vbz_qty = sum(available_lot_ids.mapped('quantity'))

class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    use_lot_for_finished_product = fields.Boolean("Use same lot for finished product")


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    user_workcenter_id = fields.Many2one("mrp.workcenter", "Workcenter", compute="_compute_user_workcenter_id")
    done_workcenter_id = fields.Many2one("mrp.workcenter", "Workcenter Used")

    def _compute_user_workcenter_id(self):
        for workorder in self:
            workorder.user_workcenter_id = self.env.user.workcenter_id

    @api.model
    def _get_name_backorder(self, name, sequence):
        if not sequence:
            return name
        if name[-4:-3] == "-" and int(name[-3:]) == sequence:
            return name
        seq_back = "-" + "0" * (SIZE_BACK_ORDER_NUMERING - 1 - int(math.log10(sequence))) + str(sequence)
        regex = re.compile(r"-\d+$")
        if regex.search(name) and sequence > 1:
            return regex.sub(seq_back, name)
        return name + seq_back


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    custom_location_id = fields.Many2one("stock.location", "Workcenter Location", help="Location used for workcenter fixed per user")

    def action_work_order(self):
        workorder_id = self.env['mrp.workorder'].search([('production_id.state', '=', 'progress'),
                                    ('workcenter_id', '=', self.id)], limit=1)
        if workorder_id:
            workorder_id.open_tablet_view()
        else:
            next_workorder = self.env['mrp.workorder'].get_next_workorder(workcenter_id=self.id)
            if next_workorder:
                return next_workorder.open_tablet_view()
        return self.env['mrp.workorder'].um_mrp_workorder_todo()


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    user_workcenter_id = fields.Many2one("mrp.workcenter", "Workcenter", compute="_compute_user_workcenter_id")
    done_workcenter_id = fields.Many2one("mrp.workcenter", "Workcenter Used")
    use_lot_for_finished_product = fields.Boolean("Use lot for finished product", compute="_compute_use_lot_for_finished_product")
    # repaired_mo_count = fields.Integer()
    repaired_mo_domain = fields.Many2many(comodel_name='mrp.production',string='Domain for repaired MOs', compute='_get_repaired_mo_domain')
    component_stock_quant_domain = fields.Many2many(comodel_name='stock.quant',string='Domain for SN', compute='_get_component_stock_quant_domain')
    component_lot_id_domain = fields.Many2many(comodel_name='stock.production.lot',string='Domain for SN', compute='_get_component_lot_id_domain')

    @api.depends('production_id.repaired_ids')
    def _get_repaired_mo_domain(self):
        for record in self:
            record.repaired_mo_domain = False

            # if self.is_first_step:

            repair_productions = self.production_id.procurement_group_id.mrp_production_ids.filtered(
                lambda x: 
                    x.has_returned_from_repair and \
                    x.state not in ('to_close', 'done', 'cancel')
            )

            record.repaired_mo_domain = repair_productions
            # record.repaired_mo_count = len(repair_productions)
            # repair_production_with_scanned_barcode = repair_productions.filtered(
            #     lambda x: x.lot_producing_id.name == barcode and \
            #     x.state not in ('to_close', 'done', 'cancel')
            # )
            # if repair_production_with_scanned_barcode:
            #     repair_workorder = repair_production_with_scanned_barcode.workorder_ids[0]
            #     return {'repair_workorder': repair_workorder.id}

    @api.depends('component_id')
    def _get_component_lot_id_domain(self):
        for workorder in self:
            workorder.component_lot_id_domain = False
            workorder.component_lot_id_domain = workorder.component_stock_quant_domain.mapped('lot_id')

    @api.depends('component_id')
    def _get_component_stock_quant_domain(self):
        for workorder in self:
            available_stock_quants = workorder.env['stock.quant'].search([('quantity','>',0),('product_id', '=', workorder.component_id.id),('location_id.is_stc_vbz','=',True)])

            # available_lot_ids = available_stock_quants.mapped('lot_id')
            #If current production has child production. Then - if currently recorded component was 
            #produced in child production, then only show it in table, instead of showing all component lots
            #in that location.
            child_production_id = workorder.production_id.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids - workorder.production_id
            
            if child_production_id:
                if workorder.component_id == child_production_id[0].product_id:
                    lot_ids = child_production_id.mapped('lot_producing_id')
                    available_stock_quants = available_stock_quants.filtered(lambda x: x.lot_id in lot_ids)

            #Filter lot lines, that was already assigned
            if workorder.move_line_ids:
                for mv_ln in workorder.move_line_ids:
                    #Filter only those move_lines lots,that was already registered for current component
                    if mv_ln.qty_done > 0:
                        available_stock_quants = available_stock_quants.filtered(
                            lambda x: x.lot_id != mv_ln.lot_id
                        )

            workorder.component_stock_quant_domain = available_stock_quants

    def _compute_use_lot_for_finished_product(self):
        for workorder in self:
            use_lot_for_finished_product = False
            if any([x.use_lot_for_finished_product for x in workorder.production_bom_id.bom_line_ids]):
                use_lot_for_finished_product = True
            workorder.use_lot_for_finished_product = use_lot_for_finished_product
    
    # @api.onchange('lot_id')
    # def onchange_lot_id(self):
        # for workorder in self:
        #     # Conditional statement below is a quick fix for Odoo native code bug:
        #     # sometimes Odoo workorders copy 'lot_id' field and this allows users
        #     # to consume already-consumed intermediate products which causes
        #     # SN inheritance issues. TODO: Find why lot_id is copied and fix it
        #     if self.move_raw_ids:
        #         for move in self.move_raw_ids.filtered(lambda x: x.bom_line_id and x.bom_line_id.use_lot_for_finished_product):
        #             register_inter_product_qp = self.check_ids.filtered(lambda qp: qp.component_id == move.product_id and qp.test_type == 'register_consumed_materials')
        #             if register_inter_product_qp and register_inter_product_qp.lot_id and register_inter_product_qp.lot_id not in workorder.component_lot_id_domain:
        #                 workorder.current_quality_check_id.lot_id = False
        #                 raise UserError(f'{register_inter_product_qp.lot_id.name} could not be located in VBZ, please try again!')

    def _compute_user_workcenter_id(self):
        for workorder in self:
            workorder.user_workcenter_id = self.env.user.workcenter_id

    def do_finish(self):
        res = super(MrpWorkorder, self).do_finish()

        if res.get('domain'):  # We are going to have a domain all the time that our workcenter doesn't have any other product to produce
            _logger.info("There are no workorders in same MO, trying to find a new one")
            next_workorder = self.get_next_workorder()
            if next_workorder:
                return next_workorder.open_tablet_view()
        
        elif res.get('res_id'):
            workorder = self.browse(res['res_id'])
            if self.env.user.workcenter_id and workorder.workcenter_id != self.env.user.workcenter_id:
                _logger.info("The workorder that we are going to process differs from user workcenter.")
                next_workorder = self.get_next_workorder()
                if next_workorder:
                    return next_workorder.open_tablet_view()
        
        return res

    def get_next_workorder(self, workcenter_id=False):
        if not workcenter_id:
            if self:
                workcenter_id = self.workcenter_id.id
            if not self:
                raise ValueError("get next workorder needs workcenter_id or a model")
        workorder_id = False
        split = True

        #Dont take to next workorder which is 'returned from repair'.
        # domain = [('production_id.has_returned_from_repair', '=', False)]

        if self:
            #Here we will try to get already started WO for same MO, 
            #because we have to continue that. Try to get firstly order that didint returned from repair.
            #Because repaired orders has to go to the end of production.
            _logger.info("Getting in progress workorder for same work center and same MO and that didint returned from repair.")
            domain = [
                ('production_id.has_returned_from_repair', '=', False),
                ('production_id.state', '=', 'progress'),
                ('workcenter_id', '=', self.workcenter_id.id),
                ('production_id', 'in', self.production_id.ids + self.production_id.procurement_group_id.mrp_production_ids.ids)]
            workorder_id = self.search(domain, limit=1)
            if workorder_id:
                #Dont split, because existing 'in progress' workorder is still running.
                split = False
        
        if not workorder_id:
            #Here we will try to get already started WO for same MO, 
            #because we have to continue that. If we couldnt find any workorders before
            #now we can look for orders that returned from repair.
            _logger.info("Getting in progress workorder for same work center and same MO")
            domain = [('production_id.state', '=', 'progress'),
                ('workcenter_id', '=', self.workcenter_id.id),
                ('production_id', 'in', self.production_id.ids + self.production_id.procurement_group_id.mrp_production_ids.ids)]
            workorder_id = self.search(domain, limit=1)
            if workorder_id:
                #Dont split, because existing 'in progress' workorder is still running.
                split = False

        if not workorder_id:
            # Ready workorders associated with an alternative workcenter but the same manufacturing order; if found,
            # duplicate the manufacturing order with quantity=1, reduce quantity of original manufacturing order by 1,
            # and open tablet view of a workorder associated with the duplicate manufacturing order; if not found,
            # carry on search with the lower priority criteria
            _logger.info("Getting next workorder on alternative workcenter")
            domain = [('production_id.state', '=', 'progress'),
                                        ('workcenter_id.alternative_workcenter_ids', '=', workcenter_id),
                                        ('production_id', '=', self.production_id.id),
                                        ('production_id.product_qty', '>', 1)]
            workorder_id = self.search(domain, limit=1)
            
        if not workorder_id:
            # backorder = mo._generate_backorder_productions(close_mo=False)
            # Ready workorders associated with the same workcenter but any manufacturing order; if found,
            # open tablet view of a single such workorder, if not found, carry on search with the
            # lower priority criteria
            _logger.info("Getting next workorder on same workcenter but other MO")
            domain = [('workcenter_id', '=', workcenter_id),
                ('production_id.product_qty', '>', 1),
                ('production_id.state', '=', 'progress'),
            ]
            workorder_id = self.search(domain, limit=1)

        if not workorder_id:
            # Ready workorders associated with an alternative workcenter but any manufacturing order; if found,
            # open tablet view of a single such workorder; if not found, then there must be no workorders for either
            # of the workcenters (nothing planned) so direct user to a kanban view of workorders where we already
            # have an active listener.
            _logger.info("Getting next workorder on alternative workcenter and other MO")
            domain = [('workcenter_id.alternative_workcenter_ids', '=', workcenter_id),
                                        ('production_id.product_qty', '>', 1),
                                        ('production_id.state', '=', 'progress')]
            workorder_id = self.search(domain, limit=1)

        if workorder_id and workorder_id.production_id.product_qty > 1 and split:
            production_ids = workorder_id.production_id._split_productions({workorder_id.production_id: [workorder_id.production_id.product_qty - 1, 1]})
            production = production_ids[1]  # In theory last value should be the workorder with 1
            for workorder in production.workorder_ids:
                if production.user_workcenter_id and workorder.workcenter_id != production.user_workcenter_id:
                    production.done_workcenter_id = production.user_workcenter_id
                    # We will update the workcenter for the splitted in order to know what
                    workorder.workcenter_id = production.user_workcenter_id

                    if not workorder.workcenter_id.custom_location_id:
                        raise UserError("Workcenter %s doesn't have a custom location set" % workorder.workcenter_id.name)
                    if not production.user_workcenter_id.custom_location_id:
                        raise UserError(
                            "Workcenter %s doesn't have a custom location set" % production.user_workcenter_id.name)

                    # TODO: Should we move it only when workcenters differ? If not let's move it out "if"
                    for move in production.move_raw_ids:
                        move.location_dest_id = production.user_workcenter_id.custom_location_id.id
                        for line in move.move_line_ids:
                            line.location_dest_id = production.user_workcenter_id.custom_location_id.id

                    for move in production.move_finished_ids:
                        move.location_id = production.user_workcenter_id.custom_location_id.id
                        for line in move.move_line_ids:
                            line.location_id = production.user_workcenter_id.custom_location_id.id

            return production.workorder_ids[0]  # Assuming that we will use only 1
        else:
            return workorder_id
        _logger.info("No workorder was found")
        return False

    def refresh_tablet_view(self):
        # This action allows 'refreshing' tablet view without refreshing tab on a browser;
        # This is useful because we have a non-stored computed domain for component_lot_id
        for workorder in self:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.workorder',
                'views': [[workorder.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id, 'form']],
                'res_id': workorder.id,
                'target': 'fullscreen',
                'flags': {
                    'withControlPanel': False,
                    'form_view_initial_mode': 'edit',
                },
                'context': {
                    'from_production_order': workorder.env.context.get('from_production_order'),
                    'from_manufacturing_order': workorder.env.context.get('from_manufacturing_order')
                },
            }


    # Override
    def open_tablet_view(self):
        self.ensure_one()

        #If child manufacturing produced lets stay 40 of 100 qties, then in current manufacturing
        #order in workorder instantly set that we are producing 40 qties, because by default
        #it started work order with 100.
        childs_mos = self.production_id.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids - self.production_id
        if childs_mos and self.production_id.product_id.tracking not in ('serial') and \
        childs_mos[0].product_id.tracking not in ('serial'):
            qty_to_produce = 0
            childs_mos = self.production_id.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids - self.production_id
            child_mos_done = childs_mos.filtered(lambda x: x.state in ('done'))
            child_orders_qty_produced = sum(child_mos_done.mapped('qty_producing'))

            qty_to_produce = child_orders_qty_produced

            backorders_mos = self.production_id.procurement_group_id.mrp_production_ids - self.production_id
            backorders_mos_done = backorders_mos.filtered(lambda x: x.state in ('done'))
            if backorders_mos_done:
                backorders_qty_produced = sum(backorders_mos_done.mapped('qty_producing'))
                qty_to_produce -= backorders_qty_produced

        # Added if we start the workorder from a workcenter that is not ours will try to split it and replace the self
        if self.env.user.workcenter_id and self.env.user.workcenter_id != self.workcenter_id:
        # if self.env.user.workcenter_id and self.env.user.workcenter_id != self.workcenter_id and self.production_id.product_qty > 1:
            next_workorder = self.get_next_workorder(workcenter_id=self.workcenter_id.id)
            if next_workorder:
                self = next_workorder

        #If it tries to open last WO of currently produced batch, and it was already started by other workcenter
        #then dont let it open. This is to avoid opening same last WO by two workcenters.
        if self.env.user.workcenter_id and self.env.user.workcenter_id != self.workcenter_id and self.production_id.product_qty == 1 \
        and self.state in ('progress'):
            return self.action_work_order_kanban()
        
        if not self.is_user_working and self.working_state != 'blocked' and self.state in ('ready', 'waiting', 'progress', 'pending'):
            self.button_start()

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id, 'form']],
            'res_id': self.id,
            'target': 'fullscreen',
            'flags': {
                'withControlPanel': False,
                'form_view_initial_mode': 'edit',
            },
            'context': {
                'from_production_order': self.env.context.get('from_production_order'),
                'from_manufacturing_order': self.env.context.get('from_manufacturing_order')
            },
        }

        #Adding all of these below, because the url didint had 'action=' parameter
        #so when reloading page it was taking to other form that was not tablet view.
        #This fixes it.
        home_action = self.env.user.action_id
        if home_action:
            # return home_action.read()[0] 
            url = '/web#action=' + str(home_action.id) + '&view_type=' + 'form' + '&model=' + 'mrp.workorder'
            # if menu_id:
            #     url += '&menu_id=' + str(menu_id)
            url += '&active_id=' + str(self.id) + '&id=' + str(self.id)
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'self',
            }

        return action

        

    def record_production(self):
        if not self:
            return True

        self.ensure_one()
        self._check_sn_uniqueness()
        self._check_company()
        # self.inherit_SN()
        # We do 'check availability' on one-level-upper MO
        source_production_ids = self.production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids - self.production_id        
        source_production_ids.action_assign()

        res = super(MrpWorkorder, self).record_production()

        return res

    def _next(self, continue_production=False):
        self.inherit_SN()
        res = super()._next(continue_production=continue_production)
        return res

    def inherit_SN(self):
        """If currently recorded component's 'use_lot_for_finished_product' field
        is True, then ihnerit its SN."""
        if self.move_id and self.move_id.bom_line_id and self.move_id.bom_line_id.use_lot_for_finished_product:
            lot_id = self.env['stock.production.lot'].search([
                ('name', '=', self.lot_id.name),
                ('product_id', '=', self.production_id.product_id.id),
                ('company_id', '=', self.move_id.company_id.id),
                ('produced_class', '=', self.lot_id.produced_class),
            ])
            if not lot_id:
                lot_id = self.env['stock.production.lot'].create({
                    'name': self.lot_id.name,
                    'produced_class': self.lot_id.produced_class,
                    'product_id': self.production_id.product_id.id,
                    'company_id': self.move_id.company_id.id,
                })
            self.finished_lot_id = lot_id

    # def inherit_SN(self):
    #     """
    #     We inherit SN from an intermediate product. We know that some raw material is
    #     an intermediate product if a check-box 'use_lot_for_finished_product' is true
    #     in a related mrp.bom.line. We use quality control point (QP) data. QP of interest
    #     is such that has test_type == 'register_consumed_materials' and and the component_id
    #     matches bom_line_id.product_id with bom_line_id.use_lot_for_finished_product set to True.
    #     """
    #     if self.production_id.product_id.tracking != 'none' and not self.finished_lot_id and self.move_raw_ids:
    #         for move in self.move_raw_ids.filtered(lambda x: x.bom_line_id and x.bom_line_id.use_lot_for_finished_product and x.move_line_ids):
    #             register_intermediate_product_quality_point = self.check_ids.filtered(lambda qp: qp.component_id == move.product_id and qp.test_type == 'register_consumed_materials')
    #             if register_intermediate_product_quality_point:
    #                 lot_id = self.env['stock.production.lot'].create({
    #                     'name': register_intermediate_product_quality_point[0].lot_id.name,
    #                     'product_id': self.production_id.product_id.id,
    #                     'company_id': move.company_id.id
    #                 })
    #                 self.finished_lot_id = lot_id
