from itertools import groupby
from operator import itemgetter

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.tools.misc import OrderedSet


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    calibration_spoilage = fields.Float(string='Brokas')


    # Umina edit: modified this function, to not throw exception when changing
    # lot for product, while other product already has same lot
    @api.constrains('lot_id', 'product_id')
    def _check_lot_product(self):
        for line in self:
            continue
            # if line.lot_id and line.product_id != line.lot_id.sudo().product_id:
            #     raise ValidationError(_(
            #         'This lot %(lot_name)s is incompatible with this product %(product_name)s',
            #         lot_name=line.lot_id.name,
            #      

    def ecowood_process_product(self, new_product_id):
        """Method to generate new product on process. For example:
        generates "Kalibruotos lentos' from 'Isdziovintos lentos".

        Args:
            new_product_id (int): product id for newly processed product.
        """
        for record in self:
            # Remove primary products quants, from which secondary product will be generated
            primary_stock_quant = self.env['stock.quant'].search([
                ('product_id', '=', record.product_id.id),
                ('location_id', '=', record.location_dest_id.id),
                ('lot_id', '=', record.lot_id.id),
            ], limit=1)

            # Do nothing if stock moving sorted lameles from OUT to WH
            if primary_stock_quant:
                primary_stock_quant.update({
                    'quantity': primary_stock_quant.quantity - record.qty_done
                })
                # Delete record, if its zero
                if not primary_stock_quant.quantity:
                    primary_stock_quant.sudo().unlink()

            # update or create stock quants for secondary product
            secondary_product_quant = self.env['stock.quant'].search([
                ('product_id', '=', new_product_id),
                ('location_id', '=', record.location_dest_id.id),
                ('lot_id', '=', record.lot_id.id),
            ], limit=1)
            if secondary_product_quant:
                secondary_product = self.env['product.product'].browse([new_product_id])
                secondary_stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', secondary_product.id),
                    ('location_id', '=', record.location_dest_id.id),
                ], limit=1)
                secondary_product_quant.update({
                    'quantity': secondary_stock_quant.quantity + record.qty_done
                })
            else:
                secondary_product_quant = self.env['stock.quant'].create({
                    'product_id': new_product_id,
                    'location_id': record.location_dest_id.id,
                    'lot_id': record.lot_id.id,
                    'quantity': record.qty_done
                })

            lot_id = record.env['stock.production.lot'].browse([record.lot_id.id])
            # Set lot with new product that was produced
            record.env.cr.execute(f"UPDATE stock_production_lot set product_id={new_product_id} WHERE id={lot_id.id}")
            return primary_stock_quant, secondary_product_quant

class StockMove(models.Model):
    _inherit = 'stock.move'

    # 6.1
    type = fields.Char(related="lot_id.type_of")

    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    lot_name = fields.Char('Lot/Serial Number Name')
    thickness = fields.Float(related='lot_id.thickness', string='Storis (mm)')
    width = fields.Float(related='lot_id.width', string='Plotis (mm)')
    length1 = fields.Float(related='lot_id.length1', string='Ilgis (mm)')
    volume = fields.Float(related='lot_id.volume', string='Apimtis (m3)')

    calibration_spoilage_from_past_processes = fields.Float(
        help='Calibration spoilage, that comes from previous processes')
    calibration_spoilage = fields.Float(compute='_compute_calibration_spoilage')

    quantity_squared_of = fields.Float(related='lot_id.quantity_squared')
    calibration_state = fields.Selection([('ready', 'Ready'), ('in_progress', 'In Progress'),
                                          ('done', 'Done'), ], string='Status',
                                         default='ready', readonly=True,
                                         help="when state is set to Done, this entry can't be opened by caning barcode")

    @api.depends('calibration_spoilage_from_past_processes', 'move_line_ids.calibration_spoilage')
    def _compute_calibration_spoilage(self):
        for record in self:
            record.calibration_spoilage = sum(
                record.mapped('move_line_ids.calibration_spoilage')) + record.calibration_spoilage_from_past_processes

    @api.onchange('thickness', 'width', 'length1', "product_uom_qty")
    def _get_volume(self):
        for rec in self:
            try:
                self.volume = self.thickness * self.width * self.length1 * self.product_uom_qty
            except Exception as e:
                print(e)

    @api.onchange('product_id', 'lot_id', 'location_id')
    def _ecowood_set_product_uom_qty(self):
        """Automatically set product_uom_qty with qty value found in stock.quant
        that has same lot_id, product_id and location_id"""
        for record in self:
            record.product_uom_qty = 0
            stock_quant = False
            if record.location_id and record.product_id \
                    and record.lot_id:
                stock_quant = record.env['stock.quant'].search([
                    ('location_id', '=', record.location_id.id),
                    ('product_id', '=', record.product_id.id),
                    ('lot_id', '=', record.lot_id.id),
                ])
            if stock_quant:
                record.product_uom_qty = sum(stock_quant.mapped('quantity'))

    def create_new_sp(self, picking_type_id=False, product_id=False, spoilage=0):
        """ Creates Stock.piking:
            Operation Type: Pervezimas i Kalibravima IN: Kalibravimas OUT

        """
        for record in self:
            order_lines = []
            # Append order lines and create new transfer with a calibrated plank product
            product_id = product_id if product_id else record.product_id
            order_lines.append(
                (0, 0,
                 {
                     'product_id': product_id.id,
                     'lot_id': record.lot_id.id,
                     'product_uom': product_id.uom_id.id,
                     'company_id': record.env.user.company_id.id,
                     'name': product_id and product_id.name or record.product_id.name,
                     'location_id': picking_type_id.default_location_src_id.id,
                     'location_dest_id': picking_type_id.default_location_dest_id.id,
                     'product_uom_qty': record.product_uom_qty,
                     'calibration_spoilage_from_past_processes': spoilage,
                 }
                 ))

            picking_id = record.env['stock.picking'].create({
                'picking_type_id': picking_type_id.id,
                'location_id': picking_type_id.default_location_src_id.id,
                'location_dest_id': picking_type_id.default_location_dest_id.id,
                'move_lines': order_lines,
                'move_type': 'direct',
            })

            picking_id.action_confirm()

    def _action_assign(self):
        """ Reserve stock moves by creating their stock move lines. A stock move is
        considered reserved once the sum of `product_qty` for all its move lines is
        equal to its `product_qty`. If it is less, the stock move is considered
        partially available.
        """

        def _get_available_move_lines(move):
            move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
            keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

            def _keys_in_sorted(ml):
                return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

            grouped_move_lines_in = {}
            for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
                qty_done = 0
                for ml in g:
                    qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                grouped_move_lines_in[k] = qty_done
            move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move) \
                .filtered(lambda m: m.state in ['done']) \
                .mapped('move_line_ids')
            # As we defer the write on the stock.move's state at the end of the loop, there
            # could be moves to consider in what our siblings already took.
            moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
            moves_out_siblings_to_consider = moves_out_siblings & (
                    StockMove.browse(assigned_moves_ids) + StockMove.browse(partially_available_moves_ids))
            reserved_moves_out_siblings = moves_out_siblings.filtered(
                lambda m: m.state in ['partially_available', 'assigned'])
            move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped(
                'move_line_ids')
            keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

            def _keys_out_sorted(ml):
                return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)

            grouped_move_lines_out = {}
            for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
                qty_done = 0
                for ml in g:
                    qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                grouped_move_lines_out[k] = qty_done
            for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted),
                                key=itemgetter(*keys_out_groupby)):
                grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
            available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in
                                    grouped_move_lines_in}
            # pop key if the quantity available amount to 0
            rounding = move.product_id.uom_id.rounding
            return dict(
                (k, v) for k, v in available_move_lines.items() if float_compare(v, 0, precision_rounding=rounding) > 0)

        StockMove = self.env['stock.move']
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
        # cache invalidation when actually reserving the move.
        reserved_availability = {move: move.reserved_availability for move in self}
        roundings = {move: move.product_id.uom_id.rounding for move in self}
        move_line_vals_list = []
        # Once the quantities are assigned, we want to find a better destination location thanks
        # to the putaway rules. This redirection will be applied on moves of `moves_to_redirect`.
        moves_to_redirect = OrderedSet()
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            rounding = roundings[move]
            missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity,
                                                                           move.product_id.uom_id,
                                                                           rounding_method='HALF-UP')
            if move._should_bypass_reservation():
                # create the move line(s) but do not impact quants
                if move.move_orig_ids:
                    available_move_lines = _get_available_move_lines(move)
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        qty_added = min(missing_reserved_quantity, quantity)
                        move_line_vals = move._prepare_move_line_vals(qty_added)
                        move_line_vals.update({
                            'location_id': location_id.id,
                            'lot_id': lot_id.id,
                            'lot_name': lot_id.name,
                            'owner_id': owner_id.id,
                        })
                        move_line_vals_list.append(move_line_vals)
                        missing_reserved_quantity -= qty_added
                        if float_is_zero(missing_reserved_quantity, precision_rounding=move.product_id.uom_id.rounding):
                            break

                if missing_reserved_quantity and move.product_id.tracking == 'serial' and (
                        move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                    for i in range(0, int(missing_reserved_quantity)):
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=1))
                elif missing_reserved_quantity:
                    to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                                       ml.location_id == move.location_id and
                                                                       ml.location_dest_id == move.location_dest_id and
                                                                       ml.picking_id == move.picking_id and
                                                                       not ml.lot_id and
                                                                       not ml.package_id and
                                                                       not ml.owner_id)
                    if to_update:
                        to_update[0].product_uom_qty += move.product_id.uom_id._compute_quantity(
                            missing_reserved_quantity, move.product_uom, rounding_method='HALF-UP')
                    else:
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
                assigned_moves_ids.add(move.id)
                moves_to_redirect.add(move.id)
            else:
                if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                elif not move.move_orig_ids:
                    if move.procure_method == 'make_to_order':
                        continue
                    # If we don't need any quantity, consider the move assigned.
                    need = missing_reserved_quantity
                    if float_is_zero(need, precision_rounding=rounding):
                        assigned_moves_ids.add(move.id)
                        continue
                    # Reserve new quants and create move lines accordingly.
                    forced_package_id = move.package_level_id.package_id or None
                    available_quantity = move._get_available_quantity(move.location_id, package_id=forced_package_id)

                    if available_quantity <= 0:
                        continue

                    # Umina edit: reserve only for provided lot (because by standard it takes whatever lot
                    # it can find)
                    lot_id = False
                    if move.lot_id:
                        lot_id = self.env['stock.production.lot'].browse([move.lot_id.id])
                    taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id,
                                                                    package_id=forced_package_id, strict=False,
                                                                    lot_id=lot_id)

                    taken_quantity = 5
                    if float_is_zero(taken_quantity, precision_rounding=rounding):
                        continue
                    moves_to_redirect.add(move.id)
                    if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
                        assigned_moves_ids.add(move.id)
                    else:
                        partially_available_moves_ids.add(move.id)
                else:
                    # Check what our parents brought and what our siblings took in order to
                    # determine what we can distribute.
                    # `qty_done` is in `ml.product_uom_id` and, as we will later increase
                    # the reserved quantity on the quants, convert it here in
                    # `product_id.uom_id` (the UOM of the quants is the UOM of the product).
                    available_move_lines = _get_available_move_lines(move)
                    if not available_move_lines:
                        continue
                    for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
                        if available_move_lines.get((move_line.location_id, move_line.lot_id,
                                                     move_line.result_package_id, move_line.owner_id)):
                            available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id,
                                                  move_line.owner_id)] -= move_line.product_qty
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
                        # `quantity` is what is brought by chained done move lines. We double check
                        # here this quantity is available on the quants themselves. If not, this
                        # could be the result of an inventory adjustment that removed totally of
                        # partially `quantity`. When this happens, we chose to reserve the maximum
                        # still available. This situation could not happen on MTS move, because in
                        # this case `quantity` is directly the quantity on the quants themselves.
                        available_quantity = move._get_available_quantity(location_id, lot_id=lot_id,
                                                                          package_id=package_id, owner_id=owner_id,
                                                                          strict=True)
                        if float_is_zero(available_quantity, precision_rounding=rounding):
                            continue
                        taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity),
                                                                        location_id, lot_id, package_id, owner_id)
                        if float_is_zero(taken_quantity, precision_rounding=rounding):
                            continue
                        moves_to_redirect.add(move.id)
                        if float_is_zero(need - taken_quantity, precision_rounding=rounding):
                            assigned_moves_ids.add(move.id)
                            break
                        partially_available_moves_ids.add(move.id)
            if move.product_id.tracking == 'serial':
                move.next_serial_count = move.product_uom_qty

        self.env['stock.move.line'].create(move_line_vals_list)
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
        if self.env.context.get('bypass_entire_pack'):
            return
        self.mapped('picking_id')._check_entire_pack()
        try:
            StockMove.browse(moves_to_redirect).move_line_ids._apply_putaway_strategy()
        except Exception as e:
            print(e)
        # Umina edit: on reserved quantities, instantly set qty_done too
        for move in self:
            for mv_line in move.move_line_ids:
                mv_line.qty_done = mv_line.product_uom_qty
