from odoo import models, fields


class UminaFinalProduct(models.Model):
    _inherit = 'product.product'

    is_final_product = fields.Boolean('Is Final Product', help='This check-box will act as an identifier of the actually final product (we have many produced products but majority of them are intermediate, that is, are consumed at later manufacturing stages). If this check-box is checked, then the product product will be transferred to the packing zone after being produced. Also, if this check-box is checked, then user will be allowed to change variation of the product according to configuration in this Bill of Material.')
