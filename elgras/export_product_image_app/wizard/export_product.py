# -*- coding: utf-8 -*-

import base64
from io import BytesIO

import xlsxwriter
from PIL import Image

from odoo import fields, models


def get_product_with_max_attachments(products):
    """returns product with most attachments"""
    products_with_max_attachments = 0
    for item in products:
        picture_count = len(item.pictures_ids)
        if picture_count > products_with_max_attachments:
            products_with_max_attachments = picture_count
    return products_with_max_attachments


def get_product_with_max_packaging(products):
    """returns product with most packaging"""
    products_with_max_attachments = 0
    for item in products:
        picture_count = len(item.packaging_ids)
        if picture_count > products_with_max_attachments:
            products_with_max_attachments = picture_count
    return products_with_max_attachments


class ExportProduct(models.TransientModel):
    _name = 'export.product'
    _description = 'Export Product Report'

    file = fields.Binary("Download Excel File")
    file_name = fields.Char(string="File Name")

    def resize_image_data(self, file_path, bound_width_height):
        # get the image and resize it
        im = Image.open(file_path)
        im.thumbnail(bound_width_height, Image.ANTIALIAS)  # ANTIALIAS is important if shrinking

        # stuff the image data into a bytestream that excel can read
        im_bytes = BytesIO()
        im.save(im_bytes, format='PNG')
        return im_bytes

    def export_product_xls(self):
        name_of_file = 'Export Product Information.xls'
        file_path = 'Export Product Information' + '.xls'
        workbook = xlsxwriter.Workbook('/tmp/' + file_path)
        worksheet = workbook.add_worksheet('Export Product Information')
        header_format = workbook.add_format(
            {'bold': True, 'valign': 'vcenter', 'font_size': 16, 'align': 'center', 'bg_color': '#D8D8D8'})
        title_format = workbook.add_format(
            {'border': 1, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'font_size': 14, 'bg_color': '#D8D8D8'})
        cell_wrap_format_bold = workbook.add_format(
            {'border': 1, 'bold': True, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'center', 'font_size': 12,
             'bg_color': '#D8D8D8'})  ##E6E6E6
        cell_wrap_format = workbook.add_format(
            {'border': 1, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'left', 'font_size': 12, })  ##E6E6E6
        cell_wrap_format_right = workbook.add_format(
            {'border': 1, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'right', 'font_size': 12, })  ##E6E6E6
        cell_text_wrap_format = workbook.add_format(
            {'text_wrap': True, 'border': 1, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'left',
             'font_size': 12, })  ##E6E6E6
        cell_text_wrap_format.set_text_wrap()

        # Add a number format for cells with money.
        money_format = workbook.add_format({'num_format': '#,##0'})
        # Merge Row Columns
        TITLEHEDER = 'Eksportuoti produktų informaciją'

        column_product_image = 0
        column_internal_reference = 1
        column_barcode = 2
        column_product_title = 3
        column_product_sell_price = 4
        column_product_buy_price_last = 5
        column_product_forecasted_quantity = 6

        column_product_description = 7

        column_product_weight_default = 8

        column_product_length = 9
        column_product_width = 10
        column_product_height = 11
        column_product_depth = 12
        column_product_weight = 13
        column_product_other_dimensions = 14
        column_product_materials = 15

        last_row = column_product_materials

        worksheet.set_column(first_col=0, last_col=0, width=25)
        worksheet.set_column(1, 1, 20)
        worksheet.set_column(2, 2, 10)
        worksheet.set_column(column_product_title, column_product_title, 30)
        worksheet.set_column(4, 4, 15)
        worksheet.set_column(5, 5, 20)
        worksheet.set_column(6, 6, 20)
        worksheet.set_column(7, 7, 28)
        worksheet.set_column(8, 8, 20)
        worksheet.set_column(9, 12, 20)
        worksheet.set_column(column_product_other_dimensions, column_product_other_dimensions, 29)
        worksheet.set_column(14, 30, 20)

        active_ids = self._context['active_ids']
        products = self.env['product.product'].browse(active_ids)
        rowscol = 1
        worksheet.set_row(rowscol, 20)

        worksheet.write(rowscol + 2, column_product_image, 'Photo', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_internal_reference, 'Internal Reference', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_barcode, 'Barcode', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_title, 'Title', cell_wrap_format_bold)

        worksheet.write(rowscol + 2, column_product_sell_price, 'Sell price', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_buy_price_last, 'Buying price', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_forecasted_quantity, 'Forecasted Quantity', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_description, 'Description', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_weight_default, 'Package Weight', cell_wrap_format_bold)

        # Package info from Product->General Information (TAB)-> Product data
        worksheet.write(rowscol + 2, column_product_length, 'Product Length', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_width, 'Product Width', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_height, 'Product Height', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_depth, 'Product Depth', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_weight, 'Product Weight', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_other_dimensions, 'Product Other Dimensions', cell_wrap_format_bold)
        worksheet.write(rowscol + 2, column_product_materials, 'Product Materials', cell_wrap_format_bold)

        rows = (rowscol + 3)

        extend_header = 0
        row_counter = 0
        # Package names x_studio fields from (Product Variants->Inventory 10 elements)
        for count, name_of_package in enumerate(
                ["Package 1 (LxWxH)", "Package 2 (LxWxH)", "Package 3 (LxWxH)", "Package 4 (LxWxH)",
                 "Package 5 (LxWxH)", "Package 1 weight, kg", "Package 2 weight, kg", "Package 3 weight, kg",
                 "Package 4 weight, kg", "Package 5 weight, kg"]):
            worksheet.write(rowscol + 2, last_row + 1 + count, f'{name_of_package}',
                            cell_wrap_format_bold)
            row_counter += 1
            extend_header += 1

        # Add pictures
        pictures_starts_at = last_row + row_counter + 1
        product_with_most_images = get_product_with_max_attachments(products)
        for count in range(product_with_most_images):
            worksheet.write(rowscol + 2, last_row + row_counter + 1 + count, f'Photo {count + 1}',
                            cell_wrap_format_bold)
            extend_header += 1
        worksheet.merge_range(1, 0, 0, last_row + extend_header, TITLEHEDER, header_format)

        # Start to add products here
        for item in products:
            if item.categ_id.is_component_category:
                # Dont print if product is component
                continue
            if item.image_1920:
                prod_img = BytesIO(base64.b64decode(item.image_1920))
                bound_width_height = (270, 90)
                image_data = self.resize_image_data(prod_img, bound_width_height)
                worksheet.insert_image(rows, column_product_image, "product_image.png", {'image_data': image_data})
                worksheet.set_row(rows, 90)

            # worksheet.set_row(rows, 30)

            worksheet.write(rows, column_internal_reference, item.default_code or '', cell_wrap_format)
            worksheet.write(rows, column_barcode, item.barcode or '', cell_wrap_format)
            worksheet.write(rows, column_product_title, item.name or '', cell_text_wrap_format)
            worksheet.write(rows, column_product_description,
                            item.product_description.strip() if item.product_description else '',
                            cell_text_wrap_format)
            worksheet.write(rows, column_product_weight_default, item.weight or '', cell_text_wrap_format)

            worksheet.write(rows, column_product_sell_price, item.lst_price or '', cell_text_wrap_format)

            worksheet.write(rows, column_product_buy_price_last, item.standard_price or '',
                            cell_wrap_format_right)
            worksheet.write(rows, column_product_forecasted_quantity, item.virtual_available or '',
                            cell_wrap_format_right)

            # Package info from Product->General Information (TAB)-> Product data
            worksheet.write(rows, column_product_length, item.product_length or '',
                            cell_wrap_format_right)
            worksheet.write(rows, column_product_width, item.product_width or '',
                            cell_wrap_format_right)
            worksheet.write(rows, column_product_height, item.product_height or '',
                            cell_wrap_format_right)
            worksheet.write(rows, column_product_depth, item.product_depth or '',
                            cell_wrap_format_right)
            worksheet.write(rows, column_product_weight, item.product_weight or '',
                            cell_wrap_format_right)
            worksheet.write(rows, column_product_other_dimensions, item.product_other_dimensions or '',
                            cell_wrap_format_right)
            worksheet.write(rows, column_product_materials, item.product_other_dimensions or '',
                            cell_wrap_format_right)

            row_to_insert = last_row + 1
            # Package 1 (LxWxH)
            worksheet.write(rows, row_to_insert + 0, item.x_studio_package_1_lxwxh, cell_text_wrap_format)
            worksheet.write(rows, row_to_insert + 1, item.x_studio_package_2_lxwxh, cell_text_wrap_format)
            worksheet.write(rows, row_to_insert + 2, item.x_studio_package_3_lxwxh, cell_text_wrap_format)
            worksheet.write(rows, row_to_insert + 3, item.x_studio_package_4_lxwxh, cell_text_wrap_format)
            worksheet.write(rows, row_to_insert + 4, item.x_studio_package_5_lxwxh, cell_text_wrap_format)
            worksheet.write(rows, row_to_insert + 5, item.x_studio_package_1_weight_kg, cell_text_wrap_format)
            # Package 1 weight, kg
            worksheet.write(rows, row_to_insert + 6, item.x_studio_package_2_weight_kg, cell_text_wrap_format)
            worksheet.write(rows, row_to_insert + 7, item.x_studio_package_3_weight_kg, cell_text_wrap_format)
            worksheet.write(rows, row_to_insert + 8, item.x_studio_package_4_weight_kg, cell_text_wrap_format)
            worksheet.write(rows, row_to_insert + 9, item.x_studio_package_5_weight_kg, cell_text_wrap_format)

            # Add Many Product pictures
            web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            picture_ids = reversed(list(item.pictures_ids))
            for count, image in enumerate(picture_ids):
                # fix here for other formats if .pdf is attached for example
                if image.image_src:
                    worksheet.write(rows, pictures_starts_at + count, web_base_url + image.image_src,
                                    cell_text_wrap_format)
            rows = rows + 1  # Add second row

        workbook.close()
        export_id = base64.b64encode(open('/tmp/' + file_path, 'rb+').read())
        result_id = self.env['export.product'].create({'file': export_id, 'file_name': name_of_file})
        return {
            'name': 'Export Product with Images',
            'view_mode': 'form',
            'res_id': result_id.id,
            'res_model': 'export.product',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
