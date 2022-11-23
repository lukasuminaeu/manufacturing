from odoo import fields, models


class PartnerPlatform(models.Model):
    """Automatically display fields only with tags defined in domain
        4.22
    """
    _inherit = 'sale.order'
    domain = ['|',
              ('category_id', '=', "Platforma"),
              ('category_id', '=', "Platforma2")
              ]
    extension_platform_id = fields.Many2one("res.partner", domain=domain)
    extension_platform_order_number = fields.Char()
    is_production = fields.Boolean(compute="_compute_is_production")

    def _compute_is_production(self):
        for rec in self:
            conf = self.env["ir.config_parameter"]
            rec.is_production = conf.sudo().get_param("dpd.is_production")


class PartnerPlatformInvoices(models.Model):
    """Automatically display fields only with tags defined in domain
        4.22
    """
    _inherit = 'account.move'
    sales_order = fields.Many2one("sale.order")
    extension_refer_platform = fields.Char(compute="_compute_platform")
    extension_refer_extension_platform_order_number = fields.Char(compute="_compute_order_number")

    move_line_ids = fields.Many2many('stock.move.line', compute='_compute_acc_move_lines')
    crm_file_upload = fields.Binary()

    def _compute_acc_move_lines(self):
        """Fill Order Line Notebook field"""
        self.ensure_one()
        quotation = self.env['sale.order'].search(
            [('state', '!=', 'cancel'), ('name', '=', self.invoice_origin)])
        if not quotation:
            # TODO: fix when clicking create on sales / prob there is better way of doing this
            self.move_line_ids = [(6, 0, [0])]
        for order in quotation:
            move_lines = []
            order_picking_ids = order.picking_ids
            print(order_picking_ids)

            packages_and_items = {}
            # Set uniques packages only once, to display in Quotations "Siuntu Statusai"
            for product in order_picking_ids.move_line_ids:
                package = product.result_package_id.display_name
                packages_and_items[package] = product
            move_lines += [x.id for x in packages_and_items.values()]

            self.move_line_ids = [(6, 0, move_lines)]

    def _compute_platform(self):
        self.ensure_one()
        quotation = self.env['sale.order'].search(
            [('state', '!=', 'cancel'), ('name', '=', self.invoice_origin)])
        self.extension_refer_platform = quotation.extension_platform_id.display_name

    def _compute_order_number(self):
        for rec in self:
            quotation = self.env['sale.order'].search(
                [('state', '!=', 'cancel'), ('name', '=', rec.invoice_origin)], limit=1)
            rec.extension_refer_extension_platform_order_number = quotation.extension_platform_order_number
