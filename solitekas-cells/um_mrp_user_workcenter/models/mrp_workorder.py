
import logging
from odoo import models, fields, _, api

_logger = logging.getLogger(__name__)

class MRPWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    def action_open_manufacturing_order(self):
        return self.retry_on_db_failure(method='action_open_manufacturing_order', parent=super())

    @api.model
    def um_mrp_workorder_todo(self):
        # Returns action with domain. Domain is taken from res.users object for current user
        #to filter workcenters that is set in user object, or in its alternative_workcenter_ids field
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.mrp_workorder_action_tablet")
        # action = self.env["ir.actions.actions"]._for_xml_id("um_mrp_user_workcenter.um_mrp_workorder_action_tablet")
        user_workcenter = self.env.user.workcenter_id
        alternative_workcenter = user_workcenter.alternative_workcenter_ids
        action['context'] = False
        # # action['context'] = {'active_id': 1}
        action['domain'] = f"""[
            ('state', 'in', ['ready', 'progress']),
            '|',
            ('workcenter_id', '=', {user_workcenter.id}),
            ('workcenter_id', '=', {alternative_workcenter.id}),
        ]"""

        action['target'] = 'fullscreen'
        action['flags'] = {
            'form_view_initial_mode': 'edit',
            'withControlPanel': False,
            'no_breadcrumbs': True,
        }
        return action
