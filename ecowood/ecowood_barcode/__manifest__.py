# -*- coding: utf-8 -*-
{
    'name': "ecowood_barcode",

    'summary': """
        Ecowood project modifications for barcode module.""",

    'description': """
        Now its possible to scan lot number in the barcode scanning menu.
        It will instantly open the first stock.move.line from picking, that
        you can edit and save.
    """,

    'author': "Umina",
    'website': "https://umina.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock_barcode', 'um_lots', 'stock'],
    'license': 'LGPL-3',

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/stock_report_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'ecowood_barcode/static/src/**/*.js',
        ],

    }
}
