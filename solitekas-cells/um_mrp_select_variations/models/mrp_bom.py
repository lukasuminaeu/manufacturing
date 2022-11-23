from odoo import models, fields, api


class BoMSelectVariation(models.Model):
    _inherit = 'mrp.bom'

    is_final_product = fields.Boolean(related='product_tmpl_id.product_variant_id.is_final_product', help='This check-box will act as an identifier of the actually final product (we have many produced products but majority of them are intermediate, that is, are consumed at later manufacturing stages). If this check-box is checked, then the product product will be transferred to the packing zone after being produced. Also, if this check-box is checked, then user will be allowed to change variation of the product according to configuration in this Bill of Material (see page Variations below).')
    variants_ids = fields.Many2many(
        comodel_name='product.product', string='Variants', domain='[("product_tmpl_id","=",product_tmpl_id), ("product_template_variant_value_ids","!=",False)]')
    variation_rules_ids = fields.One2many(
        string='Variation rules', comodel_name='mrp.production.variation.rules', inverse_name='bom_id')

    def create_variation_rules(self):
        for bom in self:
            related_boms = bom.ids
            bom_lines_for_variation_rules = []
            while related_boms:
                related_bom = bom.env['mrp.bom'].browse(related_boms[0])
                for bom_line in related_bom.bom_line_ids:
                    if bom_line.child_bom_id:
                        related_boms.append(bom_line.child_bom_id.id)
                    else:
                        bom_lines_for_variation_rules.append(bom_line.id)
                related_boms.remove(related_bom.id)

            # Create variation rule lines for new variation rules
            for variant in bom.variants_ids.filtered(lambda v: v not in bom.variation_rules_ids.mapped('product_id')):
                for bom_line in bom_lines_for_variation_rules:
                    bom_line_object = variant.env['mrp.bom.line'].browse(
                        bom_line)
                    rule_vals = {
                        'bom_id': bom.id,
                        'mrp_bom_line_id': bom_line_object.id,
                        'product_id': variant.id,
                        'component_before_id': bom_line_object.product_id.id,
                        'component_after_id': bom_line_object.product_id.id,
                        'product_qty_before': bom_line_object.product_qty,
                        'product_qty_after': bom_line_object.product_qty,
                        'replace_or_new': 'replace'
                    }
                    bom.variation_rules_ids = [(0,0,rule_vals)]
            
            # Delete excessive variation rules
            disjoint_variants = set(bom.variation_rules_ids.mapped('product_id').ids) - set(bom.variants_ids.ids)
            bom.variation_rules_ids.filtered(lambda v: v.product_id.id in disjoint_variants).unlink()



    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            if self.product_id.product_tmpl_id != self.product_tmpl_id:
                self.product_id = False
            self.bom_line_ids.bom_product_template_attribute_value_ids = False
            self.operation_ids.bom_product_template_attribute_value_ids = False
            self.byproduct_ids.bom_product_template_attribute_value_ids = False

            # Umina change: we don't need to override self.code below

            # domain = [('product_tmpl_id', '=', self.product_tmpl_id.id)]
            # if self.id.origin:
            #     domain.append(('id', '!=', self.id.origin))
            # number_of_bom_of_this_product = self.env['mrp.bom'].search_count(domain)
            # if number_of_bom_of_this_product:  # add a reference to the bom if there is already a bom for this product
            #     self.code = _("%s (new) %s", self.product_tmpl_id.name, number_of_bom_of_this_product)
            # else:
            #     self.code = False

            # Umina change end
