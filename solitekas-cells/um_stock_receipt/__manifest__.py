# -*- encoding: utf-8 -*-

{
    'name': 'Umina Stock Receipt',
    'version': '1.0',
    'category': 'Stock',
    'sequence': 50,
    'summary': 'Umina Stock Receipt',
    'depends': ['stock', 'product'],
    'description': """

""",
    'data': [
        'views/stock_views.xml',
        'report/product_product_templates.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_backend': [
            'um_stock_receipt/static/src/**/*.js',
            'um_stock_receipt/static/src/**/*.css',
        ],
        'web.assets_qweb': [
            'um_stock_receipt/static/src/**/*.xml',
        ],
    },
    'application': False,
    'license': 'LGPL-3',
}
