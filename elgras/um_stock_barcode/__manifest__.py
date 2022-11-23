# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Elgras Umina Barcode Stock',
    'version': '2.0',
    'category': 'Customizations',
    'summary': 'Umina Barcode Stock DPD extension',
    'depends': ['stock_barcode'],
    'description': """

""",
    'assets': {
        'web.assets_backend': [
            'um_stock_barcode/static/src/**/*.js',
        ],
        'web.assets_qweb': [
            'um_stock_barcode/static/src/**/*.xml',
        ],
    },
    'application': True,
    #'sequence': -1,
    'license': 'LGPL-3',
}
