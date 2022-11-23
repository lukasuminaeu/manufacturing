# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import _serialize_exception
from odoo.tools import html_escape

import json


class StockReportController(http.Controller):

    @http.route('/um_stock_barcode/<string:output_format>/<int:package_id>', type='http', auth='user')
    def report(self, output_format, package_id, **kw):
        uid = request.session.uid
        package_id = int(package_id)
        stock_quant_package = request.env['stock.quant.package'].with_user(uid)
        try:
            if output_format == 'pdf':
                report = request.env.ref('stock.action_report_quant_package_barcode')
                pdf_content, _ = report.sudo()._render_qweb_pdf(package_id)

                response = request.make_response(
                    pdf_content,
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', 'attachment; filename=' + 'report_package_barcode' + '.pdf;')
                    ]
                )
                return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
