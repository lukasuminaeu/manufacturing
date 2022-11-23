from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class UminaWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    needs_repairing = fields.Boolean(related='production_id.needs_repairing')
    to_be_scrapped = fields.Boolean(related='production_id.to_be_scrapped')


    def compute_available_qty_source_mos(self):
        source_mos = self.production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids - self.production_id
        source_mos = source_mos.filtered(lambda x: x.state in ('confirmed', 'progress'))
        source_mos.action_assign()

    def action_open_manufacturing_order(self):
        print('111')
        # Umina change: no_start_next=True -> no_start_next=False
        action = self.with_context(no_start_next=False).do_finish()
        print('333')
        # try:
        #     with self.env.cr.savepoint():
        res = self.production_id.button_mark_done()
        print('444')

        self.production_id._check_repairing()
        print('555')
        test = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id)
        ])
        print('test123')
        print(test)
        print(test.mapped('location_id'))
        self.production_id._check_scrap()
        print('666')

        if self.production_id.lot_producing_id.produced_class == 'C':
            self.scrap_one_product()
            self.produce_class_c_product()
            self.discount_source_qty()

        print('777')
        
        if res is not True:
            res['context'] = dict(res['context'], from_workorder=True)
            return res
                    
        print('888')
        # except (UserError, ValidationError) as e:
        #     # log next activity on MO with error message
        #     self.production_id.activity_schedule(
        #         'mail.mail_activity_data_warning',
        #         note=e.name,
        #         summary=('The %s could not be closed') % (self.production_id.name),
        #         user_id=self.env.user.id) # <--- TODO: user_id should be manufacturing administrator not workcenter
            
            # Workcenters should never be directed to the form view
            # return {
            #     'type': 'ir.actions.act_window',
            #     'res_model': 'mrp.production',
            #     'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
            #     'res_id': self.production_id.id,
            #     'target': 'main',
            # }
        

        #On done and next, if currently produced product is not tracket by serial number, then do some computations.
        #Check how much is already produced in current stage, so exact amount would be set in parent order.
        parent_mos = self.production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids - self.production_id
        parent_mos = parent_mos.filtered(lambda x: x.state not in ('done', 'cancel', 'to_close'))
        if parent_mos and parent_mos.product_id.tracking not in ('serial') and \
        parent_mos[0].product_id.tracking not in ('serial'):
            self.compute_available_qty_source_mos()

        # #On done and next, if currently produced product is not tracket by serial number, then do some computations.
        # #Check how much is already produced in current stage, so exact amount would be set in parent order.
        # parent_mos = self.production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids - self.production_id
        # parent_mos = parent_mos.filtered(lambda x: x.state not in ('done', 'cancel', 'to_close'))
        # if parent_mos and parent_mos.product_id.tracking not in ('serial') and \
        # parent_mos[0].product_id.tracking not in ('serial'):
        #     parent_mos[0].workorder_ids[0].um_compute_possible_workorder_qty()

        # self.test111()
        
        return action
    
    def action_work_order_kanban(self):
        for workorder in self:
            home_action = self.env.user.action_id
            if home_action:
                return self.env["ir.actions.actions"]._for_xml_id(self.env['ir.actions.act_window'].browse([home_action.id]).xml_id)
                # return home_action.read()[0] 

            action = workorder.um_mrp_workorder_todo()
            return action

    def action_previous(self):
        #Fix for 'Previous' button. Now after clicking it, if we are currently in
        #'passfail' step, then it will reverse scraps and repairs that was set primarely.
        res = super().action_previous()
        
        if self.test_type == 'passfail':
            self.production_id.write({'needs_repairing': False})
            self.production_id.write({'to_be_scrapped': False})
        
        return res