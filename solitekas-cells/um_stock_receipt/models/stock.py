import math
from pickle import EMPTY_LIST, EMPTY_SET
from odoo import models, fields, _, api
from odoo.exceptions import UserError
from collections import Counter, defaultdict


class StockPickingPackages(models.Model):
    _name = "stock.picking.packages"
    _description = "This model allows selecting a package and associating all or some of the content with a picking"
    _rec = 'name'

    name = fields.Char('Name', default=lambda p: f'{p.product_id.name} in {p.package_id.name}')

    picking_id = fields.Many2one('stock.picking','Picking')
    product_id = fields.Many2one('product.product','Product')
    package_id = fields.Many2one('stock.quant.package','Package')
    quant_inside = fields.Float('Available', help='This is the quantity of the product found in the package', compute='_get_quant_inside')
    quant_used = fields.Float('Quantity', help='This is the quantity of the product used in the picking', default=lambda p: p.quant_inside)

    @api.depends('product_id','package_id')
    def _get_quant_inside(self):
        for picking_package in self:
            picking_package.quant_inside = sum(picking_package.package_id.quant_ids.filtered(lambda q: q.product_id.id == picking_package.product_id.id).mapped('quantity'))

class StockPicking(models.Model):
    _inherit = "stock.picking"

    fifo_or_select = fields.Selection(selection=[('fifo','FIFO Packages'),('select','Select Packages')], default='fifo')
    select_package_id = fields.Many2one(comodel_name='stock.quant.package',string='Use Package')
    select_packages_ids = fields.One2many(comodel_name='stock.picking.packages',string="Package & QTY", inverse_name='picking_id')

    def test111(self):
        print('11aa')
        test = self.select_packages_ids.create({
            'package_id': 39,
        })

        self.select_packages_ids += test

    def _update_transfer_origin_by_main(self):
        """Update transfer origin field with value
        of main_production_id manufacturing order name."""
        # mo = self.env['mrp.production'].search([('name', '=', self.origin)])
        # main_production_id = mo.compute_main_production_id()
        # if mo and main_production_id:
        #     self.origin = main_production_id.name

    @api.model
    def create(self, vals):
        res = super().create(vals)
        # res._update_transfer_origin_by_main()
        return res

    @api.onchange('fifo_or_select')
    def clear_stock_move_lines(self):
        for picking in self:
            picking.move_line_ids_without_package.unlink()

    def remove_selected_package(self):
        for picking in self:
            picking.select_packages_ids.filtered(lambda p: p.package_id.id == picking.select_package_id.id).unlink()
            picking.move_line_ids_without_package.filtered(lambda p: p.package_id.id == picking.select_package_id.id).unlink()

    def remove_selected_packages(self):
        for picking in self:
            picking.select_packages_ids.unlink()

    @api.onchange('select_packages_ids')
    def _update_selected_packages_ids(self):
        for picking in self:
            picking.move_line_ids_without_package = False
            for line in picking.select_packages_ids:
                line.quant_used = line.quant_inside if line.quant_inside < line.quant_used else line.quant_used # Cannot use more than available in the package
                for qty, product_line in enumerate(line.package_id.quant_ids):
                    if qty <= line.quant_used - 1:
                        picking.move_line_ids_without_package = [(0,0,{
                            'product_id': product_line.product_id.id,
                            'package_id': line.package_id.id,
                            'lot_id': product_line.lot_id.id,
                            'qty_done': product_line.quantity,
                            'product_uom_id': product_line.product_uom_id.id,
                            'location_id': picking.location_id.id,
                            'location_dest_id': picking.location_dest_id.id
                            })]


    @api.onchange('select_package_id',)
    def _create_selected_packages_ids(self):
        for picking in self:
            if picking.select_package_id:
                uniq_products = set(picking.select_package_id.quant_ids.mapped('product_id').ids) if picking.select_package_id and picking.select_package_id.id not in picking.select_packages_ids.mapped('package_id').ids else []
                for product in uniq_products:
                    picking.select_packages_ids = [(0,0,{'product_id':product, 'package_id': picking.select_package_id.id})]
                    for line in picking.select_package_id.quant_ids.filtered(lambda p: p.product_id.id == product):
                        picking.move_line_ids_without_package = [(0,0,{
                            'product_id':product,
                            'package_id': picking.select_package_id.id,
                            'lot_id': line.lot_id.id,
                            'qty_done': line.quantity,
                            'product_uom_id': line.product_uom_id.id,
                            'location_id': picking.location_id.id,
                            'location_dest_id': picking.location_dest_id.id
                            })]
                picking.select_package_id = False

    def action_generate_picking_packings(self):
        """ Render the packing report in pdf and attach it to the picking in `self`. """
        self.ensure_one()
        package_ids = [m.result_package_id.id for m in self.move_line_ids.filtered(lambda x: x.result_package_id)]
        report = self.env.ref('stock.action_report_quant_package_barcode')._render_qweb_pdf(package_ids)
        filename = "%s_package_report" % self.name
        message = _('Packages')
        self.message_post(
            attachments=[('%s.pdf' % filename, report[0])],
            body=message,
        )
        return True


class StockMove(models.Model):
    _inherit = "stock.move"

    receipt_label = fields.Boolean("Labels")
    receipt_line_qty = fields.Integer("Line QTY")
    qty_per_package = fields.Float("Qty per Lot")
    qty_exceeded = fields.Boolean("Quantity Exceeded", compute="_is_qty_exceeded")

    def action_open_label_layout(self):
        view = self.env.ref('stock.product_label_layout_form_picking')
        return {
            'name': _('Choose Labels Layout'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.label.layout',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_product_ids': self.product_id.ids,
                'default_move_line_ids': self.move_line_nosuggest_ids.ids,
                'default_picking_quantity': 'picking'},
        }

    @api.onchange('move_line_nosuggest_ids','move_line_nosuggest_ids.lot_id', 'move_line_nosuggest_ids.lot_name')
    def _check_uniqueness_lot_names(self):
        """Raise error if scanned lot_name is in the list already.
            Made it function this way, because it was somehow not working when
            putting @api.onchange on stock.move.line.
        """
        for record in self:
            lines_lot_names = record.mapped('move_line_nosuggest_ids.lot_name')
            if lines_lot_names:
                if False in lines_lot_names:
                    lines_lot_names.remove(False)

                if len(lines_lot_names) != len(set(lines_lot_names)):
                    raise UserError('LOT pavadinimai turi būti unikalūs.')


    @api.onchange('receipt_label')
    def onchange_receipt_label(self):
        for move in self:
            move.move_line_ids.fastcreate = move.receipt_label

    @api.depends('product_uom_qty', 'quantity_done')
    def _is_qty_exceeded(self):
        for move in self:
            move.qty_exceeded = round(move.quantity_done, 2) > round(move.product_uom_qty, 2)

    @api.onchange("receipt_line_qty", "product_uom_qty")
    def onchange_receipt_line_qty(self):
        for move in self:
            move.qty_per_package = (move.receipt_line_qty and move.product_uom_qty > move.quantity_done) and (move.product_uom_qty - move.quantity_done) / move.receipt_line_qty or 0.0

    def action_generate_receipt_lines(self):
        """ On `self.move_line_ids`, assign `lot_name` according to
        `self.next_serial` before returning `self.action_show_details`.
        """
        self.ensure_one()
        self._generate_package_numbers()
        return self.action_show_details()

    def _generate_package_numbers(self, next_serial_count=False):
        """ This method will generate `lot_name` from a string (field
        `next_serial`) and create a move line for each generated `lot_name`.
        """
        self.ensure_one()
        move_lines_commands = self._generate_package_move_line_commands()
        self.write({'move_line_ids': move_lines_commands})
        return True
    
    def _generate_package_move_line_commands(self):
        """Return a list of commands to update the move lines (write on
        existing ones or create new ones).
        Called when user want to create packagings for a certain amount of lines.

        :return: A list of commands to create/update :class:`stock.move.line`
        :rtype: list
        """
        self.ensure_one()

        location_dest = self.location_dest_id._get_putaway_strategy(self.product_id, quantity=1, packaging=self.product_packaging_id)
        move_line_vals = {
            'picking_id': self.picking_id.id,
            'location_dest_id': location_dest.id,
            'location_id': self.location_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
        }

        move_lines_commands = []
        if self.picking_type_id.show_reserved:
            move_lines = self.move_line_ids
        else:
            move_lines = self.move_line_nosuggest_ids

        qty_remaining = self.product_uom_qty - self.quantity_done
        move_lines.filtered(lambda x: x.qty_done == 0.0).unlink()
        if self.receipt_line_qty:
            #move_lines.unlink()
            for package_id in range(self.receipt_line_qty):
                qty_to_be_done = qty_remaining - self.qty_per_package > 0 and self.qty_per_package or qty_remaining
                qty_remaining -= qty_to_be_done
                # if package_id + 1 == self.receipt_line_qty:  # If it is the last line
                #     qty_to_be_done = qty_remaining
                #     qty_remaining -= qty_to_be_done
                # else:
                #     qty_to_be_done = qty_remaining - self.qty_per_package > 0 and self.qty_per_package or qty_remaining
                #     qty_remaining -= qty_to_be_done
                if self.receipt_label:
                    move_line_cmd = dict(move_line_vals, qty_done=qty_to_be_done)
                else:
                    #new_package_id = self.env['stock.quant.package'].create({}).id
                    new_lot_obj = self.env['stock.production.lot'].create({
                        'product_id': self.product_id.id,
                        'name': self.env['stock.production.lot']._get_next_serial(self.company_id, self.product_id) or self.env['ir.sequence'].next_by_code('stock.lot.serial'),
                        'company_id': self.company_id.id
                        })
                    new_lot_id = new_lot_obj.id
                    #move_line_cmd = dict(move_line_vals, qty_done=qty_to_be_done, result_package_id=new_package_id)
                    move_line_cmd = dict(move_line_vals, qty_done=qty_to_be_done, lot_id=new_lot_id, lot_name=new_lot_obj.display_name)
                move_lines_commands.append((0, 0, move_line_cmd))
        elif self.receipt_line_qty == 0 and self.qty_per_package:
            #new_package_id = self.env['stock.quant.package'].create({}).id
            new_lot_obj = self.env['stock.production.lot'].create({
                'product_id': self.product_id.id,
                'name': self.env['stock.production.lot']._get_next_serial(self.company_id, self.product_id) or self.env['ir.sequence'].next_by_code('stock.lot.serial'),
                'company_id': self.company_id.id
                })
            new_lot_id = new_lot_obj
            #move_line_cmd = dict(move_line_vals, qty_done=self.qty_per_package, result_package_id=new_package_id)
            move_line_cmd = dict(move_line_vals, qty_done=self.qty_per_package, lot_id=new_lot_id.id, lot_name=new_lot_id.display_name)
            move_lines_commands.append((0, 0, move_line_cmd))

        return move_lines_commands

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # def write(self, vals):
    #     print(self)
    #     print(vals)
    #     res = super().write(vals)
    #     self.test111()
    #     return res

    # def test111(self):
    #     print('test123')
    #     tst = self.env['mrp.production.schedule'].search([
    #         ('product_id', '=', self.product_id.id),
    #     ])
    #     for i in tst:
    #         i.get_production_schedule_view_state()



    fastcreate = fields.Boolean("FastCreate", compute='_get_fastcreate')

    @api.depends('move_id', 'move_id.receipt_label')
    def _get_fastcreate(self):
        for line in self:
            line.fastcreate = line.move_id.receipt_label

    @api.onchange('lot_id', 'lot_name')
    def _onchange_lot_id_qty(self):
        for line in self:
            pending_done = line.move_id.reserved_availability - line.move_id.quantity_done
            line_qty = line.move_id.qty_per_package
            line.qty_done = line_qty and line_qty or pending_done > 0.0 and pending_done or 0.0

    @api.onchange('lot_name', 'lot_id')
    def _onchange_serial_number(self):
        """ When the user is encoding a move line for a tracked product, we apply some logic to
        help him. This includes:
            - automatically switch `qty_done` to 1.0
            - warn if he has already encoded `lot_name` in another move line
            - warn (and update if appropriate) if the SN is in a different source location than selected
        """
        res = {}
        if self.product_id.tracking == 'serial':
            if not self.qty_done:
                self.qty_done = 1

            message = None
            if self.lot_name or self.lot_id:
                # move_lines_to_check = self._get_similar_move_lines()
                move_lines_to_check = self._get_similar_move_lines() - self
                if self.lot_name:
                    counter = Counter([line.lot_name for line in move_lines_to_check])
                    # if counter.get(self.lot_name) and counter[self.lot_name] > 1:
                    if counter.get(self.lot_name) and counter[self.lot_name] > 0:
                        message = _('You cannot use the same serial number twice. Please correct the serial numbers encoded.')
                    elif not self.lot_id:
                        lots = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id),
                                                                        ('name', '=', self.lot_name),
                                                                        ('company_id', '=', self.company_id.id)])
                        quants = lots.quant_ids.filtered(lambda q: q.quantity != 0 and q.location_id.usage in ['customer', 'internal', 'transit'])
                        if quants:
                            message = _('Serial number (%s) already exists in location(s): %s. Please correct the serial number encoded.', self.lot_name, ', '.join(quants.location_id.mapped('display_name')))
                elif self.lot_id:
                    counter = Counter([line.lot_id.id for line in move_lines_to_check])
                    if counter.get(self.lot_id.id) and counter[self.lot_id.id] > 0:
                    # if counter.get(self.lot_id.id) and counter[self.lot_id.id] > 1:
                        message = _('You cannot use the same serial number twice. Please correct the serial numbers encoded.')
                    else:
                        # check if in correct source location
                        message, recommended_location = self.env['stock.quant']._check_serial_number(self.product_id,
                                                                                                     self.lot_id,
                                                                                                     self.company_id,
                                                                                                     self.location_id,
                                                                                                     self.picking_id.location_id)
                        if recommended_location:
                            self.location_id = recommended_location
            if message:
                res['warning'] = {'title': _('Warning'), 'message': message}
        return res



            
