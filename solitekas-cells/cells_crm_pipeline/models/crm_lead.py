# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, tools
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class CrmLeadCellsPipeline(models.Model):
    _inherit = 'crm.lead'

    hidden_stage = fields.Char(String='hidden stage')

    delivery_tag_ids = fields.Many2many('delivery.scope.tags', string='Delivery Scope', help="Delivery scope tags")
    installation_tag_ids = fields.Many2many('installation.type.tags', string='Installation Type', help="Delivery scope tags")
    supplier_tag_ids = fields.Many2many('supplier.tags', string='Supplier', help="Delivery scope tags")
    cell_probability = fields.Float(related='stage_id.cell_probability', string='Probability')

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        ctx = self.env.context
        # _logger.debug('\n\n %s \n\n', ctx)
        pipeline_type = ctx.get('default_hidden_stage')
        # team_id = self.env.user.sale_team_id.id

        teams_obj = self.env['crm.team'].search([('member_ids', '=', self.env.user.id)])

        team_ids = []
        for team in teams_obj:
            for item in team.pipeline_type:
                if item.name == pipeline_type:
                    team_ids.append(team.id)

        stages_by_team = self.env['crm.stage'].search([('team_id.id', 'in', team_ids)])
        # _logger.debug('\n\n %s %s %s \n\n', team_ids, stages_by_team, ctx.get('default_hidden_stage'))
        return stages_by_team

    @api.model
    def open_project_management_pipeline(self):
        no_filter = self.env.context.get('no_filter')
        if no_filter:
            return self.render_pipeline(pipeline='Project', type='opportunity', name='Project Management',
                                        filter_self=0)
        else:
            return self.render_pipeline(pipeline='Project', type='opportunity', name='Project Management',
                                        filter_self=1)

    @api.model
    def open_leads_pipeline(self):
        no_filter = self.env.context.get('no_filter')
        if no_filter:
            return self.render_pipeline(pipeline='Lead', type='opportunity', name='CRM Leads', filter_self=0)
        else:
            return self.render_pipeline(pipeline='Lead', type='lead', name='CRM Leads', filter_self=1)

    @api.model
    def open_sales_pipeline(self):
        no_filter = self.env.context.get('no_filter')
        if no_filter:
            return self.render_pipeline(pipeline='Sale', type='opportunity', name='CRM Sales', filter_self=0)
        else:
            return self.render_pipeline(pipeline='Sale', type='opportunity', name='CRM Sales', filter_self=1)

    @api.model
    def render_pipeline(self, pipeline, type, name, filter_self):
        """
            Summary of the function
            Filter CRM views by Stages and 3 types of Tags
            Returns:
            Action window for projects
        """
        teams_obj = self.env['crm.team'].search([('member_ids', '=', self.env.user.id)])
        default_team = ''
        team_ids = []
        for team in teams_obj:
            for item in team.pipeline_type:
                if item.name == pipeline:
                    default_team = team.id
                    team_ids.append(team.id)
        if not team_ids:
            raise UserError('You cannot access this pipeline, you do not belong to correct team')
            # domain = [('team_id.id', 'in', team_ids), ('type', '=', 'do_not_show_no_team_id')]
        else:
            domain = [('team_id.id', 'in', team_ids), ('type', '=', type)]
        _logger.debug('\n\n %s \n %s \n', team_ids, domain)
        ctx = {
            'default_hidden_stage': pipeline,
            'default_type': type,
            'default_team_id': default_team,
            'search_default_assigned_to_me': filter_self,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'name': name,
            'view_mode': 'kanban,tree,form,calendar,pivot,graph,activity',
            'res_model': 'crm.lead',
            'context': ctx,
            'domain': domain,
        }


class CrmStrageCellsPipeline(models.Model):
    _inherit = 'crm.stage'

    team_id = fields.Many2many('crm.team', "crm_stage_crm_team_rel", string='Sales Team',
                              help='Specific team that uses this stage. Other teams will not be able to see or use this stage.')
    cell_probability = fields.Float('Probability')


class CrmTeamCellsPipeline(models.Model):
    _inherit = 'crm.team'

    pipeline_type = fields.Many2many('crm.cells.pipeline', 'crm_pipeline_crm_team_rel', string='Pipeline access')
    member_ids = fields.Many2many(
        'res.users', 'res_user_crm_team_rel', string='Channel Members', check_company=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('base.group_user').id)],
        help="Add members to automatically assign their documents to this sales team. You can only be member of one team.")

    @api.model
    def action_cells_primary_channel_button(self, value):
        _logger.debug('------------------------------------------')
        teams_obj = self.env['crm.team'].search([('member_ids', '=', self.env.user.id)])
        team_ids = [x.id for x in teams_obj]
        team_self = self.env['crm.team'].search([('id', '=', value[0])])
        lead_obj = self.env['crm.lead']
        if value[0] in team_ids:
            _logger.debug('\n\n %s %s %s \n\n', teams_obj, value, team_self.pipeline_type[0].name)
            # actions = [
            #     {'Project': lead_obj.open_project_management_pipeline()},
            #     {'Lead': lead_obj.open_leads_pipeline()},
            #     {'Sale': lead_obj.open_sales_pipeline()},
            # ]
            if team_self.pipeline_type[0].name == 'Project':
                return lead_obj.open_project_management_pipeline()
            elif team_self.pipeline_type[0].name == 'Lead':

                return lead_obj.open_leads_pipeline()
                
            elif team_self.pipeline_type[0].name == 'Sale':

                return lead_obj.open_sales_pipeline()
                # return actions[team_self.pipeline_type[0]]
                # _logger.debug('\n\n %s \n\n', team_self.pipeline_type[0])
        else:
            raise UserError('You cannot access this pipeline, you do not belong to correct team')

class CrmTeamCellsLead2OpPipeline(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'

    @api.onchange('team_id')
    def onchange_team_id(self):
        user_ids = []
        if self.team_id:
            if self.team_id.use_leads:
                self.user_id = False
            else:
                if self.team_id.member_ids:
                    for id in self.team_id.member_ids:
                        user_ids.append(id.id)
                    if self.user_id.id not in user_ids:
                        self.user_id = user_ids[0]
                return {'domain': {'user_id': [('id', 'in', user_ids)]}}

    # @api.model
    # def default_get(self, fields):
    #     """ Default get for name, opportunity_ids.
    #         If there is an exisitng partner link to the lead, find all existing
    #         opportunities links with this partner to merge all information together
    #     """
    #     result = super(CrmTeamCellsLead2OpPipeline, self).default_get(fields)
    #     _logger.debug('\n\n %s \n\n', result)
    #     if self._context.get('active_id'):
    #         tomerge = {int(self._context['active_id'])}
    #
    #         partner_id = result.get('partner_id')
    #         lead = self.env['crm.lead'].browse(self._context['active_id'])
    #         email = lead.partner_id.email if lead.partner_id else lead.email_from
    #
    #         tomerge.update(self._get_duplicated_leads(partner_id, email, include_lost=True).ids)
    #
    #         if 'action' in fields and not result.get('action'):
    #             result['action'] = 'exist' if partner_id else 'create'
    #         if 'partner_id' in fields:
    #             result['partner_id'] = partner_id
    #         if 'name' in fields:
    #             result['name'] = 'merge' if len(tomerge) >= 2 else 'convert'
    #         if 'opportunity_ids' in fields and len(tomerge) >= 2:
    #             result['opportunity_ids'] = list(tomerge)
    #         if lead.user_id:
    #             result['user_id'] = lead.user_id.id
    #         if lead.team_id:
    #             result['team_id'] = lead.team_id.id
    #         if not partner_id and not lead.contact_name:
    #             result['action'] = 'nothing'
    #         _logger.debug('\n\n %s \n\n', result)
    #     # return result
    #     return super(CrmTeamCellsLead2OpPipeline, self).default_get(fields)

    # @api.onchange('user_id')
    # def _onchange_user(self):
    #     """ When changing the user, also set a team_id or restrict team id
    #         to the ones user_id is member of.
    #     """
    #     if self.user_id:
    #         if self.team_id:
    #             user_in_team = self.env['crm.team'].search_count(
    #                 [('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id),
    #                  ('member_ids', '=', self.user_id.id)])
    #         else:
    #             user_in_team = False
    #         if not user_in_team:
    #             values = self.env['crm.lead']._onchange_user_values(self.user_id.id if self.user_id else False)
    #             self.team_id = values.get('team_id', False)