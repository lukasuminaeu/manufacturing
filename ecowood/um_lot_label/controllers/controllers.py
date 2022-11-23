# -*- coding: utf-8 -*-
# from odoo import http


# class UmLotLabel(http.Controller):
#     @http.route('/um_lot_label/um_lot_label', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/um_lot_label/um_lot_label/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('um_lot_label.listing', {
#             'root': '/um_lot_label/um_lot_label',
#             'objects': http.request.env['um_lot_label.um_lot_label'].search([]),
#         })

#     @http.route('/um_lot_label/um_lot_label/objects/<model("um_lot_label.um_lot_label"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('um_lot_label.object', {
#             'object': obj
#         })
