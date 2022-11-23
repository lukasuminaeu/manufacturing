# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MrpParentWorkcenter(models.Model):
    _name = 'mrp.parent.workcenter'
    _description = 'Mrp Parent Workcenter'

    name = fields.Char("Name")
    capacity = fields.Integer('Capacity')


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    parent_workcenter_id = fields.Many2one('mrp.parent.workcenter', 'Parent Workcenter')
    max_units = fields.Integer('Max Units per day', related='parent_workcenter_id.capacity')
    units_produced_percentage = fields.Float("Today's Capacity Used (%)", compute="_get_today_capacity_used")

    def _get_today_capacity_used(self):
        for workcenter in self:
            workorders = self.env['mrp.workorder'].search([('production_date', '=', fields.Date.today()), ('state', '=', 'done'), ('workcenter_id', '=', workcenter.id)])
            total_produced = 0
            for w in workorders:
                total_produced += w.qty_produced
            workcenter.units_produced_percentage = workcenter.max_units and total_produced * 100 / workcenter.max_units or 0.0


class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    max_units = fields.Integer(related='workcenter_id.max_units', string='Max Units', store=True)
    units_produced_percentage = fields.Float("Percentage of capacity used", compute="_get_capacity_used", store=True)


    @api.depends('qty_produced', 'max_units')
    def _get_capacity_used(self):
        for workorder in self:
            workorder.units_produced_percentage = workorder.max_units and workorder.qty_produced * 100 / workorder.max_units or 0.0

    def do_pass(self):
        self.ensure_one()
        # self.inherit_SN()
        """
        Check if product has just returned from repairing.
        If true, then:
            1) continue with class selection wizard
        Else:
            1) unlink manufacturing order,
            2) direct user to a tablet kanban list of workorders for a given workcenter
        """

        if self.production_id._check_repairing():
            self.current_quality_check_id.do_pass()

            #If determine class for quality check is set, then open class wizard
            if self.current_quality_check_id.point_id.determines_class:
                action = self.env.ref('um_mrp_mps.action_select_product_class').sudo().read()[0]
                action['res_id'] = self.id
            else:
                #else just function as it should supposed to function by standardd.
                return self._next()

            return action
        else:
            action = self.um_mrp_workorder_todo()
            # action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.mrp_workorder_action_tablet")
            # domain = [('state', 'in', ['ready', 'progress'])]
            # action['domain'] = domain
            # action['flags'] = {
            #     'form_view_initial_mode': 'edit',
            #     'withControlPanel': False,
            #     'no_breadcrumbs': True,
            # }
            next_workorder = self.get_next_workorder()
            if next_workorder:
                action = next_workorder.open_tablet_view()
                
            self.production_id.unlink()
            return action

    def set_class_a(self):
        if self.current_quality_check_id.point_id.determines_class:
            if self.production_id and self.production_id.lot_producing_id:
                self.production_id.lot_producing_id.produced_class = 'A'
            return self._next()

    def set_class_b(self):
        if self.current_quality_check_id.point_id.determines_class:
            if self.production_id and self.production_id.lot_producing_id:
                self.production_id.lot_producing_id.produced_class = 'B'
            return self._next()

    def set_class_c(self):
        if self.current_quality_check_id.point_id.determines_class:
            if self.production_id and self.production_id.lot_producing_id:
                self.production_id.lot_producing_id.produced_class = 'C'
            # self.scrap_one_product()
            # self.produce_class_c_product()
            # self.discount_source_qty()
            return self._next()

    def do_finish(self):
        res = super(MrpWorkOrder, self).do_finish()
        self.env['bus.bus']._sendone('mrp_production', 'workorder_update', self.id)
        # self.env['bus.bus']._sendone('mrp_workorder', 'workorder_update', self.id)
        self.env['bus.bus']._sendone('mrp_workorder', 'workorder_update', {'product_id': self.production_id.product_id.id})
        self.env['bus.bus']._sendone('mrp_workorder', 'workcenter_update', {'workcenter_id': self.workcenter_id.id})
        
        return res

    def scrap_one_product(self):
        if not self.production_id.lot_producing_id:
            raise ValidationError("Select Lot Number")
        stock_scrap = self.env['stock.scrap'].create({
            'product_id': self.production_id.product_id.id,
            'scrap_qty': 1,
            'product_uom_id': self.production_id.product_uom_id.id,
            'lot_id': self.production_id.lot_producing_id.id,
            'location_id': self.production_id.location_dest_id.id,
            'scrap_location_id': self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', '=', self.company_id.id)], limit=1).id,
            'workorder_id': self.id,
        })
        stock_scrap.do_scrap()

    def _prepare_c_move(self):
        self.ensure_one()
        if not self.production_bom_id.product_class_c:
            raise ValidationError("BoM doesn't have product class C")
        location_zone_id = self.production_id.location_dest_id.id
        dest_location_id = self.env['stock.location'].search([('is_picking_zone','=',True)],limit=1).id
        # dest_location_id = self.env['stock.location'].search([('name', 'ilike', 'Packing Zone')], limit=1).id
        product_class_c = self.production_bom_id.product_class_c
        lot_id = self.env['stock.production.lot'].search([('product_id', '=', product_class_c.id), ('name', '=', self.production_id.lot_producing_id.name)], limit=1)
        if not lot_id:
            lot_id = self.env['stock.production.lot'].create({
                'product_id': product_class_c.id,
                'name': self.production_id.lot_producing_id.name,
                'company_id': self.company_id.id,
            })
        else:
            # In theory, this should never happen, because SNs will have the following format: YYYYMMDD<SEQUENCE> but by no means
            # should we ever allow moving an existing (produced) product
            raise UserError(f'Product {product_class_c.name} and {lot_id.name} already exists, please select a different intermediate product!')
        
        #First create that qty in location, that it later could be pushed
        #to packing zone without making qty -1 in primary location.
        self.env['stock.quant'].create({
            'product_id': product_class_c.id,
            'lot_id': lot_id.id, 
            'location_id': self.production_id.location_dest_id.id,
            'quantity': 1,
        })

        return {
            'name': self.name + ' produce class C',
            'origin': self.name + ' produce class C',
            'company_id': self.company_id.id,
            'product_id': product_class_c.id,
            'product_uom': product_class_c.uom_id.id,
            'state': 'draft',
            'product_uom_qty': 1,
            'location_id': location_zone_id,
            'location_dest_id': self.production_id.location_dest_id.id,
            'move_line_ids': [(0, 0, {'product_id': product_class_c.id,
                                      'product_uom_id': product_class_c.uom_id.id,
                                      'qty_done': 1,
                                      'location_id': location_zone_id,
                                      'location_dest_id': dest_location_id,
                                      'lot_id': lot_id.id, })],
        }

    def consume_components_for_produce(self):
        """_summary_ 
            This method will consume components for production, even though production
            was not finished. The reasoning is, that when we make certain action, that will
            produce different product than it was set initially in manufacturing order. By 
            this way we will cancel original manufacturing order and increase quantity of other product,
            so components have to be virtually consumed.
        """
        for record in self:
            for mv in record.move_raw_ids:
                for mv_line in mv.move_line_ids:
                    stock_quant = record.env['stock.quant']
                    available_qty = stock_quant._get_available_quantity(mv_line.product_id, mv_line.location_id, lot_id=mv_line.lot_id, package_id=None, owner_id=None, strict=False, allow_negative=False)
                    quantity = -mv_line.qty_done
                    stock_quant._update_available_quantity(mv_line.product_id, mv_line.location_id, quantity, lot_id=mv_line.lot_id, package_id=None, owner_id=None, in_date=None)


    def produce_class_c_product(self):
        move = self.env['stock.move'].create(self._prepare_c_move())
        moves_to_do = move._action_done()
        # if moves_to_do:
        #     self.consume_components_for_produce()

    def discount_source_qty(self):
        production_ids = self.env['mrp.production']
        current_production_ids = self.production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids
        production_ids += current_production_ids

        while production_ids.filtered(lambda x: x.state not in ['done', 'cancel']):
            production_ids += production_ids[0].procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids
            if production_ids[0].product_qty > 1:
                change_qty = self.env['change.production.qty'].create({
                    'mo_id': production_ids[0].id,
                    'product_qty': production_ids[0].product_qty - 1
                })
                change_qty.with_context(skip_activity=True).change_prod_qty()

                # production_ids[0].product_qty = production_ids[0].product_qty - 1
            else:
                production_ids[0].action_cancel()
            production_ids -= production_ids[0]

        
        
