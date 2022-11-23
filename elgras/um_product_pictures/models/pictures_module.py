# -*- coding: utf-8 -*-
#  4.1 and 4.2
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class PictureSalesTab(models.Model):
    """Displays Picture tab in 'Orders'"""
    _inherit = "sale.order.line"
    _description = "Pictures colum in list-view"

    # Display saved avatar url from attachments
    picture_url = fields.Char(string="Nuoroda į nuotrauką", related="product_id.avatar_url", )


class ProductPicturesNote(models.Model):
    """Notebook-tab in 'Products' category"""
    # _inherit = "product.template"
    _inherit = "product.product"
    pictures_tab = fields.Text(string="Nuotraukos")
    pictures_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments')

    # This variable is used in products
    avatar_url = fields.Char()

    # Notebook->Sales tab
    product_materials = fields.Char()
    product_weight = fields.Char()
    product_length = fields.Char()
    product_width = fields.Char()
    product_height = fields.Char()
    product_depth = fields.Char()
    product_other_dimensions = fields.Char()
    product_description = fields.Text()


class ListOfProductAttachments(models.Model):
    _inherit = 'ir.attachment'
    _description = "List of attachments in Product Notebook "

    def change_avatar(self):
        """
        Sets attached picture to product avatar
            'image_1920' avatar variable in 'product.template'
        """
        picture_data: bytes = self.datas
        related_record = self.env[self.res_model].browse(self.res_id)
        related_record.image_1920 = picture_data

        # setAvatar in Product model
        related_record.avatar_url = '/web/image/%s?unique=%s' % (self.id, self.checksum)

    def create(self, vals):
        """
        This function  sets product.product attachment images to public by default
        :param vals: values passed with attachment
        self.res_id = 0 - Record creation

        """
        try:
            model = vals.get("res_model")
        except AttributeError as er:
            return super().create(vals)

        if not vals:
            return super().create(vals)
        try:
            if model == "product.product" and vals.get("raw"):
                picture_public = {'public': True}
                vals.update(picture_public)
                _logger.info(f'Setting attachment access to public')
        except AttributeError as er:
            _logger.info(f'Error in ListOfProductAttachments {er}')
        return super().create(vals)
