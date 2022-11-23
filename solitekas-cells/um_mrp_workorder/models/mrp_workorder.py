# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools.safe_eval import safe_eval
from operator import attrgetter
import psycopg2
import time
import logging

_logger = logging.getLogger(__name__)

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workcenter'

    @api.model
    def _get_default_report_id(self):
        return self.env.ref('um_mrp_workorder.action_report_workorder', False)

    report_id = fields.Many2one('ir.actions.report',
                                string="Label Report", domain="[('model','=','mrp.workorder'),('report_type','=','qweb-pdf')]",
                                default=_get_default_report_id)

    hide_automatic_validation = fields.Boolean(string='Hide automatic validation')

class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    hide_continue_consumption = fields.Boolean('Hide Continue Consumption', compute='hide_continue_consumption_button', store=False, help='When this is true, the Continue Consumption button will be hidden. This is important, because when we register intermediate product, we inherit their SN. If we allow registering two intermediate products, then the logic fails.')
    component_intermediate_product = fields.Boolean(related='move_id.bom_line_id.use_lot_for_finished_product', help='Check if current product is intermediate product.')
    hide_automatic_validation = fields.Boolean(related='workcenter_id.hide_automatic_validation')

    def action_open_manufacturing_order(self):
        return self.retry_on_db_failure(method='action_open_manufacturing_order', parent=super())
        
    def action_next(self):
        return self.retry_on_db_failure(method='action_next', parent=super())

    def action_continue(self):
        return self.retry_on_db_failure(method='action_continue', parent=super())

    def automatic_workorder_validation(self):
        quant_to_use = self.env['stock.quant']
        if self.component_stock_quant_domain:
            max_attr = min(self.component_stock_quant_domain, key=attrgetter('lot_id.id'))
            self.lot_id = max_attr.lot_id.id
            quant_to_use = max_attr
        else:
            self.lot_id = False

        response_action = self.barcode_scan_check_component_lot(quant_to_use.lot_id.name)

        res = False
        if response_action['button_name'] == 'next':
            res = self.action_next()
        elif response_action['button_name'] == 'continue':
            res = self.action_continue()

        # return
        #All below seems to be working.
        # res = self.action_next()
        self.env.cr.commit()
        try:
            if not self.is_last_step:
                res = self.automatic_workorder_validation()
            else:
                res = self.action_open_manufacturing_order()
        except:
            return res

        return res


    def hide_continue_consumption_button(self):
        for workorder in self:
            if workorder.current_quality_check_id:
                if workorder.current_quality_check_id.test_type == 'register_consumed_materials' and workorder.current_quality_check_id.component_id.tracking == 'serial':
                    workorder.hide_continue_consumption = True
                else:
                    workorder.hide_continue_consumption = False
            else:
                workorder.hide_continue_consumption = False
                

    @api.depends('production_availability')
    def _compute_state(self):
        # Force the flush of the production_availability, the wo state is modify in the _compute_reservation_state
        # It is a trick to force that the state of workorder is computed as the end of the
        # cyclic depends with the mo.state, mo.reservation_state and wo.state
        for workorder in self:
            if workorder.state not in ('waiting', 'ready'):
                continue
            if workorder.production_id.reservation_state not in ('waiting', 'confirmed', 'assigned'):
                continue
            if workorder.production_id.reservation_state == 'assigned' and workorder.state == 'waiting':
                workorder.state = 'ready'
            elif workorder.production_id.reservation_state != 'assigned' and workorder.state == 'ready':
                workorder.state = 'waiting'
            # workorder.env['bus.bus']._sendone('mrp_production', 'workorder_update', {})
            # workorder.env['bus.bus']._sendone('mrp_workorder', 'workorder_update', {})
    
    @api.model_create_multi
    def create(self, values):
        # self.env['bus.bus']._sendone('mrp_production', 'workorder_update', {})
        # self.env['bus.bus']._sendone('mrp_workorder', 'workorder_update', {})
        return super(MrpWorkOrder, self).create(values)

    def unlink(self):
        # self.env['bus.bus']._sendone('mrp_production', 'workorder_update', {})
        # self.env['bus.bus']._sendone('mrp_workorder', 'workorder_update', {})
        return super(MrpWorkOrder, self).unlink()
    
    def action_generate_serial(self):
        super(MrpWorkOrder, self).action_generate_serial()
        return self.sudo().print_workorder_label()

    @api.depends('operation_id')
    def _compute_quality_point_ids(self):
        for workorder in self:
            quality_points = workorder.operation_id.quality_point_ids
            # Edvardas ADD: I comment the line below because we need QPs to be sorted by sequence
            # otherwise Odoo asks to do Pass/Fail without letting user to assign SN to intermediate product first

            # quality_points = quality_points.filtered(lambda qp: not qp.product_ids or workorder.production_id.product_id in qp.product_ids)
            quality_points = quality_points.filtered(lambda qp: not qp.product_ids or workorder.production_id.product_id in qp.product_ids).sorted(key=lambda qp: qp.sequence)
            # Change END
            workorder.quality_point_ids = quality_points

    @api.onchange('finished_lot_id')
    def check_if_sn_not_used_already(self):
        """Check if selected SN is not being used in other backorder MO's already"""
        for record in self:
            if record.finished_lot_id in record.production_id.procurement_group_id.mapped('mrp_production_ids.lot_producing_id'):
                raise UserError('Serijinis numeris jau užimtas.')

    def print_workorder_label(self):
        self.ensure_one()
        if not self.workcenter_id.report_id:
            raise UserError("Workcenter doesn't have a report configured")
        # get base url
        base_url = self.sudo().env['ir.config_parameter'].get_param('web.base.url')

        report = self.workcenter_id.report_id
        generic_name = _("Workorder")

        pdf_content, dummy = report.sudo()._render_qweb_pdf(self.id)
        if report.print_report_name:
            pdf_name = safe_eval(report.print_report_name, {'object': self})
        else:
            pdf_name = generic_name
        attachment_vals = {
            'name': pdf_name,
            'type': 'binary',
            'raw': pdf_content,
            'res_model': self._name,
            'res_id': self.id
        }
        attachment_id = self.env['ir.attachment'].sudo().create(attachment_vals)

        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }

    def um_compute_possible_workorder_qty(self):
        #If child manufacturing produced lets stay 40 of 100 qties, then in current manufacturing
        #order in workorder instantly set that we are producing 40 qties, because by default
        #it started work order with 100.
        qty_to_produce = 0
        childs_mos = self.production_id.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids - self.production_id
        child_mos_done = childs_mos.filtered(lambda x: x.state in ('done'))
        child_orders_qty_produced = sum(child_mos_done.mapped('qty_producing'))
        qty_to_produce = child_orders_qty_produced

        backorders_mos = self.production_id.procurement_group_id.mrp_production_ids - self.production_id
        backorders_mos_done = backorders_mos.filtered(lambda x: x.state in ('done', 'to_close'))
        if backorders_mos_done:
            backorders_qty_produced = sum(backorders_mos_done.mapped('qty_producing'))
            qty_to_produce -= backorders_qty_produced
    
        if qty_to_produce > 0:
            self.qty_producing = qty_to_produce
            self.production_id.qty_producing = qty_to_produce
        else:
            self.qty_producing = 0
            
        return qty_to_produce

    def button_start(self):
        self.production_id.action_assign()
        res = super().button_start()
        # childs_mos = self.production_id.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids - self.production_id
        # if childs_mos and self.production_id.product_id.tracking not in ('serial') and \
        # childs_mos[0].product_id.tracking not in ('serial'):
        #     self.um_compute_possible_workorder_qty()
        # if self.is_first_step:
        self.production_id.action_assign()

        return res

    # def on_barcode_scanned(self, barcode, skip_serial_assign=False):
    def barcode_scan_check_component_lot(self, barcode, component_remaining_qty=False):
        component_remaining_qty = self.component_remaining_qty or component_remaining_qty

        if self.is_first_step:
            repair_productions = self.production_id.procurement_group_id.mrp_production_ids.filtered(lambda x: x.has_returned_from_repair)
            repair_production_with_scanned_barcode = repair_productions.filtered(
                lambda x: x.lot_producing_id.name == barcode and \
                x.state not in ('to_close', 'done', 'cancel')
            )
            if repair_production_with_scanned_barcode:
                repair_workorder = repair_production_with_scanned_barcode.workorder_ids[0]
                return {'repair_workorder': repair_workorder.id}

        if self.component_tracking:
            lot_in_component_stock_quant_domain = self.component_stock_quant_domain.filtered(lambda x: x.lot_name == barcode)
            if lot_in_component_stock_quant_domain:
                self.lot_id = lot_in_component_stock_quant_domain[0].lot_id
            else:
                raise UserError('Nėra produkto su tokiu LOT sąraše.')

        if self.lot_id:
            #Do some logic, if lot component is being scanned
            if self.component_tracking == 'lot':
                component_in_table = self.component_stock_quant_domain.filtered(lambda x: x.lot_id == self.lot_id)
                #If component exists in table
                # if component_in_table.available_quantity:
                #If there isnt enough component for this lot, to fullfil
                #demand, initiate action_continue()
                if component_in_table.quantity < component_remaining_qty:
                    self.qty_done = component_in_table.quantity
                    # self.action_continue()

                    return {'button_name': 'continue'}

                #If there is enough component for this lot, to fullfil
                #demand, initiate action_next()
                else:
                    # ml = self.env['stock.move.line']
                    # ml._free_reservation(self.product_id.id, self.production_id.location_src_id.id, extra_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
                    self.qty_done = component_remaining_qty
                    # self.action_next()
                    return {'button_name': 'next'}

            #Umina edit: if component has 'serial' tracking, then isntantly validate
            #work order
            if self.component_id.tracking == 'serial':
                self.qty_done = component_remaining_qty
                # self.action_next()
                return {'button_name': 'next'}
        return {'button_name': barcode}


    # def on_barcode_scanned(self, barcode, skip_serial_assign=False):
    def on_barcode_scanned(self, barcode):
        #On workorder table view - if final product lot_id is not assigned,
        #then first try to assign a lot for it.
        if not self.production_id.product_tracking in ('none', False) and \
            not self.finished_lot_id and not self.production_id.lot_producing_id and \
            not self.use_lot_for_finished_product:
            # not skip_serial_assign:

            lot_id = self.env['stock.production.lot']
            finished_lot_id = lot_id.search([('name', '=', barcode), ('product_id', '=', self.production_id.product_id.id)])
            if not finished_lot_id:
                finished_lot_id = self.finished_lot_id.create({
                    'product_id': self.production_id.product_id.id,
                    'name': barcode,
                    'company_id': self.company_id.id,
                })
            self.finished_lot_id = finished_lot_id.id
            return

        # if self.component_tracking:
        #     lot_in_component_stock_quant_domain = self.component_stock_quant_domain.filtered(lambda x: x.lot_name == barcode)
        #     if lot_in_component_stock_quant_domain:
        #         self.lot_id = lot_in_component_stock_quant_domain[0].lot_id
        #     else:
        #         raise UserError('Nėra produkto su tokiu LOT sąraše.')

        #     if self.lot_id:
        #         #Do some logic, if lot component is being scanned
        #         if self.component_tracking == 'lot':
        #             component_in_table = self.component_stock_quant_domain.filtered(lambda x: x.lot_id == self.lot_id)
        #             #If component exists in table
        #             # if component_in_table.available_quantity:
        #             #If there isnt enough component for this lot, to fullfil
        #             #demand, initiate action_continue()
        #             if component_in_table.quantity < self.component_remaining_qty:
        #                 self.qty_done = component_in_table.quantity
        #                 # self.action_continue()
        #                 # return 'action_continue'

        #             #If there is enough component for this lot, to fullfil
        #             #demand, initiate action_next()
        #             else:
        #                 # ml = self.env['stock.move.line']
        #                 # ml._free_reservation(self.product_id.id, self.production_id.location_src_id.id, extra_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
        #                 self.qty_done = self.component_remaining_qty
        #                 # self.action_next()
        #                 # return 'action_next'

        #         #Umina edit: if component has 'serial' tracking, then isntantly validate
        #         #work order
        #         if self.component_id.tracking == 'serial':
        #             self.qty_done = self.component_remaining_qty
        #             # self.action_next()
        #             # return 'action_next'



        



