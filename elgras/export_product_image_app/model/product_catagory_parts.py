from odoo import models, fields


class ProductCategoryParts(models.Model):
    _inherit = 'product.category'

    """
    This is used for filtering Product parts if checked product is not exported
    """
    is_component_category = fields.Boolean(string="Komponentų Kategorija")
