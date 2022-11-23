# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Umina Barcode Stock',
    'version': '2.0',
    'category': 'Stock',
    'sequence': 50,
    'summary': 'Umina Barcode Stock',
    'depends': ['stock_barcode', 'um_mrp_data'],
    'description': """

""",
    'data': [
        'views/report_package_barcode.xml',
        'views/product_views.xml',
        'views/stock_move_line_views.xml',

        'data/locations_data.xml',
        'data/inventory_operation_types_data.xml',
        'data/product_product.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'um_stock_barcode/static/src/**/*.js',
        ],
        'web.assets_qweb': [
            'um_stock_barcode/static/src/**/*.xml',
        ],
    },
    'application': False,
    'license': 'LGPL-3',
}
