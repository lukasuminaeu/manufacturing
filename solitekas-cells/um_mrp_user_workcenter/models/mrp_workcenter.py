
import logging
from odoo import models, fields, _, api

_logger = logging.getLogger(__name__)

class MRPWorkCenter(models.Model):
    _inherit = 'mrp.workcenter'

    @api.model
    def um_mrp_workcenter_kanban_action_with_domain(self):
        #If theres home action assigned to user, then return it instead
        home_action = self.env.user.action_id
        if home_action:
            return self.env["ir.actions.actions"]._for_xml_id(self.env['ir.actions.act_window'].browse([home_action.id]).xml_id)
            # return home_action.read()[0] 

        # Returns action with domain. Domain is taken from res.users object for current user
        #to filter workcenters that is set in user object, or in its alternative_workcenter_ids field
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_workcenter_kanban_action")
        user_workcenter = self.env.user.workcenter_id
        alternative_workcenter = user_workcenter.alternative_workcenter_ids
        action['domain'] = f"""[
            '|',
            ('id', '=', {user_workcenter.id}),
            ('id', '=', {alternative_workcenter.id}),
        ]"""

        return action