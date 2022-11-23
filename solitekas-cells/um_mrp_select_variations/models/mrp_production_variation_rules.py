from odoo import models, fields, api


class SelectVariationConfigurator(models.Model):
    _name = 'mrp.production.variation.rules'
    _description = 'Records of this model will provide rules for the transformation of extended manufacturing order on selection of variant'

    bom_id = fields.Many2one(string='BoM', comodel_name='mrp.bom')
    product_id = fields.Many2one('product.product', 'Product Variant', readonly=True)
    variation_value = fields.Many2many(related='product_id.product_template_variant_value_ids', string="Variant")
    mrp_bom_line_id = fields.Many2one(
        comodel_name='mrp.bom.line', string='MRP BoM Line (Technical)')
    component_bom_id = fields.Many2one(
        related='mrp_bom_line_id.bom_id', string='Workcenter')
    component_before_id = fields.Many2one(
        related='mrp_bom_line_id.product_id', string='Original component')
    component_after_id = fields.Many2one(
        'product.product', string='New component')
    product_qty_before = fields.Float('Quantity before', readonly=True)
    product_qty_after = fields.Float('Quantity after')
    replace_or_new = fields.Selection(selection=[('replace', 'Replace Component'), (
        'new', 'New Component')], string='Replace / New', default='new')

    active_variation_rule = fields.Boolean(
        'Active Rule', help='This boolean is true if variation-specific component is different from original component or if variant production requires a new component', compute='_get_variation_rule_state')

    @api.depends('bom_id', 'product_id', 'mrp_bom_line_id', 'component_bom_id', 'component_before_id', 'component_after_id', 'product_qty_before', 'product_qty_after', 'replace_or_new')
    def _get_variation_rule_state(self):
        for rule in self:
            if (rule.component_before_id.id != rule.component_after_id.id) or (rule.product_qty_before != rule.product_qty_after) or rule.replace_or_new == 'new':
                rule.active_variation_rule = True
            else:
                rule.active_variation_rule = False
