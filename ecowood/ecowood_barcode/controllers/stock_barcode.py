# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController
from odoo.http import request


class EcowoodStockBarcodeController(StockBarcodeController):
    @http.route('/stock_barcode/scan_from_main_menu', type='json', auth='user')
    def main_menu(self, barcode, **kw):
        """ Receive a barcode scanned from the main menu and return the appropriate
            action (open an existing / new picking) or warning.
        """
        
        try_open_picking_from_lot = self._try_open_picking_from_lot(barcode)
        if try_open_picking_from_lot:
            return try_open_picking_from_lot

        self._try_open_picking(barcode)

        ret_open_picking = self._try_open_picking(barcode)
        if ret_open_picking:
            return ret_open_picking

        ret_open_picking_type = self._try_open_picking_type(barcode)
        if ret_open_picking_type:
            return ret_open_picking_type

        if request.env.user.has_group('stock.group_stock_multi_locations'):
            ret_new_internal_picking = self._try_new_internal_picking(barcode)
            if ret_new_internal_picking:
                return ret_new_internal_picking

        ret_open_product_location = self._try_open_product_location(barcode)
        if ret_open_product_location:
            return ret_open_product_location

        if request.env.user.has_group('stock.group_stock_multi_locations'):
            return {'warning': _('No picking or location or product corresponding to barcode %(barcode)s') % {'barcode': barcode}}
        else:
            return {'warning': _('No picking or product corresponding to barcode %(barcode)s') % {'barcode': barcode}}

    def _try_open_picking_from_lot(self, barcode):
        lot_id = request.env['stock.production.lot'].search([
            ('name', '=', barcode)
        ], limit=1)
        stock_move = request.env['stock.move'].search([
            ('lot_id', '=', lot_id.id),
            ('state', 'not in', ('cancel', 'done'))
        ], limit=1)

        if stock_move and stock_move.picking_id:
            action = stock_move.picking_id.with_context(barcode_open_line=True).action_open_picking_client_action()
            return {'action': action}

        return False