
import logging

from odoo import _, api, exceptions, fields, models, tools
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'

    stage_selection = fields.Selection([('opportunity', 'Opportunity'), ('lead', 'Lead'), ], 'Type', default='opportunity')
    products_ids = fields.Many2many('product.product', 'crm_lead_product_rel', 'lead_id', 'product_id', string='Products')
    product_categories = fields.Many2many(string=u'Product Categories',comodel_name='crm.lead.product.category',relation='crm_lead_product_category_model_crm_lead_rel',)
    product_quantity = fields.Selection(string=u'Product Quantity',selection=[('small','Small (<1 MW)'), ( 'medium','Medium(1Mw<>3Mw)'),('big','Big (3Mw<)')], default="small")
    product_price = fields.Float(string=u'Product Price',)
    reason_detail = fields.Text('Reason Details')

    

    @api.model
    def create(self, vals):
        self.create_activity(vals)
        return super(Lead, self).create(vals)

    def write(self, vals):
        stage = self.env['crm.stage'].browse(vals.get('stage_id'))
        # If change in stage
        if stage:
            for record in self:
                record.crm_clear_activity(record.id)
                activity_id = record.create_activity(vals)    

        self.check_stage_fields_required(stage,vals)
        vals = self.set_stage_salesperson(stage,vals)
        
        return super(Lead, self).write(vals)

    def set_stage_salesperson(self,stage,vals):
        if stage.stage_salesperson:
            vals['user_id']= stage.stage_salesperson
        return vals



    def check_stage_fields_required(self,stage,vals):
        for field in stage.fields_required:
            if not eval('self.'+field.name):
                raise exceptions.UserError(field.field_description + ' is required.' )


    def create_activity(self, vals):
        _logger.debug("----------create activity \n")
        model_id = self.env['ir.model'].search([('model', '=', 'crm.lead')]).id
        user_id = self.user_id.id
        res_id = self.id
        stage_id = vals.get('stage_id')
        stage = self.env['crm.stage'].browse(stage_id)
        deadline = False
        if stage.after_how_many_days:
            deadline = str(datetime.now().date() + timedelta(days=stage.after_how_many_days))
        if user_id and deadline:
            activity_id = self.crm_create_activity(model_id, user_id, res_id, deadline, stage.solitekas_description, stage.activity_type)
            return activity_id
        return False


    def crm_create_activity(self, res_model_id , user_id, res_id, deadline, message, activity_type_id):
        return self.env['mail.activity'].create({
            'activity_type_id': activity_type_id,
            'note': message,
            'automated': True,
            'is_system': True,
            'date_deadline': deadline,
            'res_model_id': res_model_id,
            'res_id': res_id,
            'user_id': user_id})
        

    def crm_clear_activity(self, res_id):
        for record in self:
            _logger.debug("---------clear activity\n")
            activity = self.env['mail.activity'].search([('res_id', '=', res_id),('is_system','=',True)],order='create_date ASC', limit=1 )
            activity.unlink()


    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = self.env['crm.stage'].search([('stage_selection2', '=', self._context.get('default_type'))])
        return stage_ids






